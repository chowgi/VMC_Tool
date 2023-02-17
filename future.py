def get_top_10(df):
  # Get the top 10 Highest Memory Users
  top_memory = df['vInfo'].sort_values(by='Memory',ascending=False)
  top_cpu = df['vInfo'].sort_values(by='CPUs',ascending=False)
  top_provisioned = df['vInfo'].sort_values(by='Provisioned MB',ascending=False)
  top_consumed = df['vInfo'].sort_values(by='In Use MB',ascending=False)
  vm_os_consumed = df['vPartition'].groupby('VM')['Consumed MB'].sum()
  top_os_consumed = vm_os_consumed.sort_values(ascending=False)
  return [top_memory, top_cpu, top_provisioned, top_consumed, top_os_consumed]


def authVMC():
  baseurl = 'https://console.cloud.vmware.com/csp/gateway'
  uri = '/am/api/auth/api-tokens/authorize'
  headers = {'Content-Type':'application/json'}
  payload = {'refresh_token': my_secret}
  r = requests.post(f'{baseurl}{uri}', headers = headers, params = payload)
  if r.status_code != 200:
      print(f'Unsuccessful Login Attmept. Error code {r.status_code}')
  else:
      auth_json = r.json()['access_token']
      auth_Header = {'Content-Type':'application/json','csp-auth-token':auth_json}
      print(f'Successful Login')
      return auth_Header

def sort_to_aws_instances(vm_data, instance_types):
  sorted_vms = []
  for vm, vm_info in vm_data.items():
    if vm_info['power'] == 'poweredOn':
      for instance_type, instance_info in instance_types.items(): 
        if vm_info['cpu'] <= instance_info['cpu'] and vm_info['memory'] <= instance_info['mem']:
            vm_info['instance_type'] = instance_type
            sorted_vms.append((vm, vm_info))
            break
  return sorted_vms

# function take in the sorted vm data and a instance name and returns a new list with only those virtual machinces that are of the instance type
def group_instance_types(sorted_vm_data, instance_name):
  
  list = []
  for vm, vm_info in sorted_vm_data:
    if vm_info['instance_type'] == instance_name:
      list.append(vm)
  return list

#Lists and Variables
instance_types = {'t3.micro':{'cpu': 2, 'mem': 1024},'t3.small':{'cpu': 2, 'mem': 2048}, 't3.medium':{'cpu': 2, 'mem': 4096}, 'm6i.large' : {'cpu': 2,'mem': 8192},'m6i.xlarge' : {'cpu': 4, 'mem': 16384}, 'm6.2xlarge': {'cpu': 8,'mem': 32768}, 'm6.4xlarge' : {'cpu': 16,'mem': 65536},'m6.8xlarge' : {'cpu': 32,'mem': 131072}}

def os_data(df, vm, data_type):
    group = df['vPartition'].groupby('VM')
    try:
      if data_type == 'consumed':
        return int(group['Consumed MiB'].sum()[vm])
      else:
        return int(group['Capacity MiB'].sum()[vm])
    except:
        return 'N/A'


def get_vm_data(df):
    # Create an empty dictionary to store the final result
    result = {}
  
    # Iterate over the rows in vInfo the DataFrame
    for _, row in df['vInfo'].iterrows():
        # Get the values from columns A, N, O, AK, and AL
        key = row['VM']
        value_dict = {
            'power': row['Powerstate'],
            'cpu': row['CPUs'],
            'memory': row['Memory'],
            'provisioned': row['Provisioned MiB'],
            'consumed': row['In Use MiB'],
            'os_provisioned': os_data(df, row['VM'], 'provisioned'),
            'os_consumed': os_data(df, row['VM'], 'consumed'),
            'datacenter': row['Datacenter'],
            'cluster': row['Cluster']
        }
        
        # Add the key and value_dict to the result dictionary
        result[key] = value_dict
  
    # Return the result dictionary
    return result

# Get totals for each important metric for sizing
#API key for VMware cloud
#my_secret = os.environ['SECRET_KEY']