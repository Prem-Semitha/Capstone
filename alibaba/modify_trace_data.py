
import pandas as pd


file_path = '/Users/premsemitha/capstone/demoApplication/alibaba/data/trace_0_data_modified_with_suffixes.csv'
data = pd.read_csv(file_path)


data_filtered = data[(data['um'] != '(?)') & (data['dm'] != '(?)')].copy()


unique_values = pd.unique(data_filtered[['um', 'dm']].values.ravel('K'))
rename_dict = {val: f'Service_{i+1}' for i, val in enumerate(unique_values)}


data_filtered['um'] = data_filtered['um'].map(rename_dict)
data_filtered['dm'] = data_filtered['dm'].map(rename_dict)


output_file_path = '/Users/premsemitha/capstone/demoApplication/alibaba/data/modified_trace_data.csv'
data_filtered.to_csv(output_file_path, index=False)


