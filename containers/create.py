import docker
import os
import json
import redis
import time

client = docker.from_env()

def get_or_create_network(network_name):
    try:
        network = client.networks.get(network_name)
        print(f"Network '{network_name}' already exists.")
    except docker.errors.NotFound:
        network = client.networks.create(network_name)
        print(f"Network '{network_name}' created.")
    return network

def create_json_file(container_name, data):
    json_data = data
    print(f"Creating JSON file for {container_name}: {json_data}")
    with open(f"{container_name}.json", "w") as temp_file:
        json.dump(json_data, temp_file)
        temp_file_path = temp_file.name
    return temp_file_path

def read_container_names(file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File '{file_path}' does not exist.")
    with open(file_path, 'r') as file:
        return [line.strip() for line in file.readlines()]

def get_and_rename_containers(containersFile="containers.txt", callsFile="calls.json"):
    mappedContainersFile = "".join(containersFile.split(".")[0]) + "_mapped.json"
    
    if os.path.isfile(mappedContainersFile):
        with open(mappedContainersFile) as f:
            renamed_containers = json.load(f)
        
        with open(callsFile) as f:
            calls = json.load(f)
        
        for um in list(calls.keys()): 
            for timestamp in calls[um]:
                for i, dm in enumerate(calls[um][timestamp]):
                    dm_key = list(dm.keys())[0]  # Extract the key from the dictionary
                    if dm_key in renamed_containers:
                        calls[um][timestamp][i] = {renamed_containers[dm_key]: dm[dm_key]}
                    else:
                        print(f"Warning: {dm_key} not found in renamed_containers")
            calls[renamed_containers[um]] = calls.pop(um)
        
        with open(callsFile.split(".")[0] + "_mapped.json", "w") as f:
            json.dump(calls, f)
        
        return renamed_containers.values(), calls
    
    containers = read_container_names(containersFile)
    renamed_containers = {container: f"s{i}" for i, container in enumerate(containers, 1)}
    
    if not os.path.isfile(callsFile) or os.path.getsize(callsFile) == 0:
        raise FileNotFoundError(f"File '{callsFile}' does not exist or is empty.")
    
    with open(callsFile) as f:
        calls = json.load(f)
    
    for um in list(calls.keys()): 
        for timestamp in calls[um]:
            for i, dm in enumerate(calls[um][timestamp]):
                dm_key = list(dm.keys())[0]  # Extract the key from the dictionary
                if dm_key in renamed_containers:
                    calls[um][timestamp][i] = {renamed_containers[dm_key]: dm[dm_key]}
                else:
                    print(f"Warning: {dm_key} not found in renamed_containers")
        calls[renamed_containers[um]] = calls.pop(um)
    
    with open(mappedContainersFile, "w") as f:
        json.dump(renamed_containers, f)
    
    with open(callsFile.split(".")[0] + "_mapped.json", "w") as f:
        json.dump(calls, f)
    
    return renamed_containers.values(), calls

def addContainerJob(container_names):
    while True:
        print("Menu: ")
        print("1. All Containers are sleeping")
        print("2. No Containers are sleeping")
        print("3. Some Containers are sleeping")
        option = input("Enter your choice (1/2/3): ").strip()
        match option:
            case '1': 
                return [[container_name, 0] for container_name in container_names]
            case '2': 
                return [[container_name, 1] for container_name in container_names]
            case '3':
                print("You can enter the containers that are working in ranges like 1-5, 7-10")
                print("1-1(includes both 1 and 1), 1-4(includes 1, 2, 3, 4)")
                containersWorking = input("Enter the containers that are working: ").replace(" ", "").split(",")
                working_indices = []
                for range_str in containersWorking:
                    start, end = map(int, range_str.split("-"))
                    working_indices.extend(range(start, end + 1))
                container_states = [[container_name, 0] for container_name in container_names]
                for i in working_indices:
                    container_states[i - 1][1] = 1  # Convert to zero-based index
                return container_states
            case _:
                print("Invalid choice. Please try again.")

def create_container(container_name, network_name, data, ip_address, container_job):
    print(f"Creating container {container_name} in network {network_name}")
    json_file_path = create_json_file(container_name, data)
    container = client.containers.run(
        "flask-contact-container",
        name=container_name,
        hostname=container_name[:5],
        detach=True,
        network=network_name,
        ports={'80/tcp': None},
        environment={
            "CONTAINER_NAME": container_name,
            "REDIS_IP_ADDRESS": ip_address,
            "CONTAINER_JOB": container_job
        }
    )
    os.system(f"docker cp ./{container_name}.json {container.id}:/app/calls.json")
    os.remove(json_file_path)
    print(f"Container '{container_name}' created and started.")
    return container

def create_logging_container(network_name, redis_ip):
    container = client.containers.run(
        'logging_capstone',
        name="logging_capstone",
        hostname='logging_capstone',
        detach=True,
        network=network_name,
        ports={'80/tcp': None},
        environment={"REDIS_IP_ADDRESS": redis_ip}
    )
    print(f"Logging Container '{container.id}' created and started.")
    return container

def create_redis_container(network_name):
    container = client.containers.run(
        "redis:latest", 
        name="redis_capstone", 
        hostname="redis_capstone", 
        ports={'6379/tcp': 6379},  # Expose port to host
        detach=True,
        network=network_name
    )
    print(f"Redis container started with ID: {container.id}")
    return container

def connect_to_redis(ip_address, max_retries=5, delay=5):
    redis_client = redis.StrictRedis(host=ip_address, port=6379)
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to Redis at {ip_address}:6379, attempt {attempt + 1}")
            redis_client.ping()
            print("Connected to Redis.")
            return redis_client
        except redis.exceptions.ConnectionError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise redis.exceptions.ConnectionError("Failed to connect to Redis after multiple attempts.")

def main():
    network_name = "static_application"
    container_names_file = "containers.txt"

    # Ensure the network exists
    network = get_or_create_network(network_name)

    # Read container names from file
    container_names, calls = get_and_rename_containers() 
    container_names = addContainerJob(container_names)

    # Create Redis Container
    redis_container = create_redis_container(network_name)
    redis_container.reload()
    ip_address = "localhost"  # Use localhost since we are exposing the port to the host
    print(f"Redis container IP address: {ip_address}")

    # Wait for Redis to be ready
    time.sleep(10)
    print("Redis container is up and running.")

    # Create Logging Container
    create_logging_container(network_name, ip_address)
    print("Logging container is up and running.")

    # Create and run containers
    containers = [create_container(name, network_name, calls[name] if name in calls else {}, ip_address, job) for name, job in container_names]

    print("All containers are up and running.")

    # Attempt to connect to Redis
    try:
        redis_client = connect_to_redis(ip_address)
        redis_client.set('start_time', int(time.time()))
        print("Redis Start Time value is now set at", redis_client.get('start_time'))
    except redis.exceptions.ConnectionError as e:
        print("Failed to connect to Redis:", e)

    print("Containers will start communicating")

if __name__ == "__main__":
    main()
