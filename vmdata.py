import pandas as pd
import json, datetime, os, requests

def get_rvtools_data(file_path):
    # create vInfo DF from the uploaded rvtools file
    df = pd.read_excel(file_path, sheet_name=['vInfo','vPartition','vMetaData'])

    # rename any column names with MB to MiB
    df['vInfo'].rename(columns={'Provisioned MB': 'Provisioned MiB', 
                          'In Use MB': 'In Use MiB'}, 
                 inplace=True, errors='ignore')

    # get the the relevant columns from vInfo
    vInfo = df['vInfo'].loc[:, ['VM', 'Powerstate', 'CPUs', 'Memory', 'Resource pool',
                          'Folder', 'Provisioned MiB', 'In Use MiB', 'Annotation',
                          'Datacenter', 'Cluster', 'OS according to the configuration file',
                          'OS according to the VMware Tools']]

    # rename any column names with MB to MiB
    df['vPartition'].rename(columns={'Capacity MB': 'Capacity MiB',
                                'Consumed MB': 'Consumed MiB'},
                       inplace=True, errors='ignore')

    # get the relevant columns from vPartition
    vPartition = df['vPartition'].loc[:, ['VM', 'Capacity MiB', 'Consumed MiB']]

    # Group and sum the values of the 'Capacity MiB' column based on the 'VM' column
    capacity = vPartition.groupby('VM')['Capacity MiB'].sum().reset_index()
    consumed = vPartition.groupby('VM')['Consumed MiB'].sum().reset_index()

    # Merge the resulting DataFrames with vInfo
    vInfo = pd.merge(vInfo, capacity, on='VM', how='left')
    vInfo = pd.merge(vInfo, consumed, on='VM', how='left')

    vInfo['Exclude'] = False
  
    #Get the meta data from vMetaData
    meta = df['vMetaData'].loc[:, ['xlsx creation datetime', 'Server']]
  

    return vInfo, meta


def all_resources(df):
    #creeate the place holder values including resources for poweredOff
    result = {'all': None, 'poweredOn': None, 'poweredOff': {'count': 'n/a', 'cpu': 'n/a', 'memory': 'n/a', 'in_use_mib': 'n/a', 'os_used': 'n/a'}}

    # Get resource totals for all clusters
    count = df[['VM']].count().values[0]
    cpu = df[['CPUs']].sum().values[0]
    mem = df[['Memory']].sum().values[0]
    provisioned_mib = df[['Provisioned MiB']].sum().values[0]
    in_use_mib = df[['In Use MiB']].sum().values[0]
    capacity_mib = df[['Capacity MiB']].sum().values[0]
    consumed_mib = df[['Consumed MiB']].sum().values[0]

    all_resources = {'count': count,
                  'cpu': cpu,
                  'memory': int(round(mem /1024)),
                  'provisioned_mib': int(round(provisioned_mib /1024)),
                  'in_use_mib': int(round(in_use_mib /1024)),
                  'capacity_mib': int(round(capacity_mib /1024)),
                  'consumed_mib': int(round(consumed_mib / 1024))
                  }
            # Update the dict
    result['all'] = all_resources
    # Get resource totals for all datacenters

    # Group VMs by power state
    states = df.groupby(['Powerstate'])

    for name, state in states:
        # Get resource totals for each power state
        count = state[['VM']].count().values[0]
        cpu = state[['CPUs']].sum().values[0]
        mem = state[['Memory']].sum().values[0]
        provisioned_mib = state[['Provisioned MiB']].sum().values[0]
        in_use_mib = state[['In Use MiB']].sum().values[0]
        capacity_mib = state[['Capacity MiB']].sum().values[0]
        consumed_mib = state[['Consumed MiB']].sum().values[0]

        totals = {'count': count,
                 'cpu': cpu,
                 'memory': int(round(mem /1024)),
                  'provisioned_mib': int(round(provisioned_mib /1024)),
                  'in_use_mib': int(round(in_use_mib /1024)),
                  'capacity_mib': int(round(capacity_mib /1024)),
                  'consumed_mib': int(round(consumed_mib / 1024))
                 }
        # Update the dict with the resources for each power state
        result[name] = totals
        
    return result

def grouped_by(df, col):
    result = {}
    # Group VMs by cluster and power state
    groups = df.groupby([col])
  
    for name, group in groups:
        df = group.copy()
        result[name] = all_resources(df)
        
    return result


def top_cpu(df):
  # Get the top 10 Highest CPU Users
  result = []
  top10 = df.sort_values(by='CPUs',ascending=False)[:5]
  for _, row in top10.iterrows():
    vm = (row['VM'], row['CPUs'])
    result.append(vm)
  
  return result


def top_memory(df):
  # Get the top 10 Highest Memory Users
  result = []
  top10 = df.sort_values(by='Memory',ascending=False)[:5]
  for _, row in top10.iterrows():
    vm = (row['VM'], int(round(row['Memory'] /1024)))
    result.append(vm)

  return result


def top_os_consumed(df):
  # Get the top 10 Highest Provisioned OS Users
  result = []
  grouped = df.groupby('VM')['Consumed MiB'].sum()
  top10 = grouped.sort_values(ascending=False)[:5]
  for index, value in top10.items():
    vm = (index, int(round(value /1024)))
    result.append(vm)

  return result