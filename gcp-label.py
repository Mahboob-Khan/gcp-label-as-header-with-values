import subprocess
import json
import csv
import re

# Get a list of all projects under the organization
projects = subprocess.check_output(['gcloud', 'projects', 'list', '--format=json'])


projects_json = json.loads(projects)

# Create a list to store all VM instances
vm_instances = []

# Loop through each project and get a list of VM instances
for project in projects_json:
    project_id = project['projectId']

    # Run the gcloud command to list VM instances for the project and capture the output
    vm_list = subprocess.check_output(['gcloud', 'compute', 'instances', 'list', '--project', project_id, '--format=json'])

    # Create a list to store all unique labels
    labels = set()
    
    # Parse the output as JSON
    vm_list_json = json.loads(vm_list)
    
    # Append each VM instance to the list
    for vm in vm_list_json:
        creation_time = vm['creationTimestamp'].split('T')[0]
        tags = ', '.join(vm['tags']['items']) if 'items' in vm['tags'] else ''
        subnetwork = vm['networkInterfaces'][0]['subnetwork'].split('/')[-1] if len(vm['networkInterfaces']) > 0 and 'subnetwork' in vm['networkInterfaces'][0] else ''
        private_ip = vm['networkInterfaces'][0]['networkIP'] if len(vm['networkInterfaces']) > 0 else ''
        
        #Get OS name
        license_url = vm['disks'][0]['licenses'][0]
        os_name = license_url.split("/")[-1]
        
        instance_status = vm['status']
        
        #print(instance_status)
        
        # Exclude instances with TERMINATED or STOPPED status
        if instance_status in ['TERMINATED', 'STOPPED']:
            continue

        command = f"gcloud compute instances os-inventory describe {vm['name']} --zone {vm['zone'].split('/')[-1]} --project {project_id} | grep 'Kernel'"
        try:

            result = subprocess.run(command, stdout=subprocess.PIPE, shell=True, check=True)
            output = result.stdout.decode().strip()

            # Extract kernel version
            kernel_version = output.split('\n')[0].split(': ')[1]
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                kernel_version = 'Unavailable'

        vm_instance = [
            project_id,
            vm['name'],
            vm['id'],
            kernel_version,
            instance_status,
            creation_time,
            vm['zone'].split('/')[-1],
            vm['machineType'].split('/')[-1],
            tags,
            subnetwork,
            private_ip,
            os_name
        ]
        
        # Create a list to store all Labels of instances
        header_vm_labels = ['application-name', 'automation-trigger', 'backup-policy', 'billingcode', 'businessowner', 'client', 'contactgroup', 'country', 'cs', 'cstype', 'environment', 'function', 'goog-dm', 'hostname', 'intended-environment', 'memberfirm', 'msp', 'patch-group', 'primarycontact', 'projectid', 'projectname', 'resource-severity', 'resourcegroup', 'resourcetype', 'secondarycontact', 'sid', 'solution-name', 'vnedormanaged']

        # Loop through each label for the VM instance
        if 'labels' in vm and vm['labels']:
            for label in header_vm_labels[0:]:
                # Check if the label exists
                if label in vm['labels']:
                    vm_instance.append(vm['labels'][label])
                else:
                    vm_instance.append("Missing")
        else:
            # Add "N/A" values for all labels
            for _ in header_vm_labels[0:]:
                vm_instance.append("Missing")

        #for label in range(len(vm_labels)):
        #    print(vm_labels[label])
            
        #    vm_instance.append(vm_labels[label])  
             
        vm_instances.append(vm_instance)        
# Create a CSV file and write the header row and VM instances
header = ['Project ID', 'VM Name', 'Instance ID', 'Kernel_version', 'Status', 'Creation Time', 'Zone', 'Machine Type', 'Tags','Subnetwork', 'Private IP', 'OS Name']

for i in range(len(header_vm_labels)):

    header.append(header_vm_labels[i])

with open('vm_inventory.csv', 'w', newline='') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(header)

    for vm_instance in vm_instances:
        writer.writerow(vm_instance)
