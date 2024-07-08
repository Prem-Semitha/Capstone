import docker
import sys

# Initialize Docker client
client = docker.from_env()

def list_containers_in_network(network_name):
    network = client.networks.get(network_name)
    return network.attrs['Containers']

def stop_and_remove_containers(container_ids):
    for container_id in container_ids:
        container = client.containers.get(container_id)
        print(f"Stopping container {container.name} ({container.id})...")
        container.stop()
        print(f"Removing container {container.name} ({container.id})...")
        container.remove()

def remove_network(network_name):
    network = client.networks.get(network_name)
    print(f"Removing network {network_name}...")
    network.remove()

def main():
    if len(sys.argv) != 2:
        print("Usage: python destroy.py <network_name>")
        sys.exit(1)

    network_name = sys.argv[1]
    
    try:
        containers = list_containers_in_network(network_name)
        container_ids = containers.keys()
        
        if not container_ids:
            print(f"No containers found in network {network_name}.")
        else:
            stop_and_remove_containers(container_ids)
        
        confirm = input(f"Do you want to remove the Docker network '{network_name}' as well? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            remove_network(network_name)
            print(f"Network {network_name} removed.")
        else:
            print(f"Network {network_name} not removed.")
    
    except docker.errors.NotFound:
        print(f"Network {network_name} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
