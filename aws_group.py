#!/usr/bin/env python3

import boto3
import json
import sys
import os

DEFAULT_USER = "ec2-user"
DEFAULT_KEY_PATH = "~/.ssh/mousa.pem"

def get_instances():
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances()

    inventory = {
        "_meta": {
            "hostvars": {}
        }
    }

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] != 'running':
                continue

            public_ip = instance.get('PublicIpAddress')
            if not public_ip:
                continue

            instance_id = instance['InstanceId']
            private_ip = instance.get('PrivateIpAddress')
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            alias = tags.get('Name', instance_id)

            # تحديد الجروب من التاج "group"، أو افتراضي
            group_name = tags.get('group', 'ungrouped')

            if group_name not in inventory:
                inventory[group_name] = {
                    "hosts": []
                }

            inventory[group_name]["hosts"].append(alias)

            inventory["_meta"]["hostvars"][alias] = {
                "ansible_host": public_ip,
                "ansible_user": DEFAULT_USER,
                "ansible_ssh_private_key_file": os.path.expanduser(DEFAULT_KEY_PATH),
                "instance_id": instance_id,
                "private_ip": private_ip,
                "tags": tags
            }

    return inventory

def write_static_inventory_file(inventory, filename="aws_inventory.ini"):
    with open(filename, 'w') as f:
        for group in inventory:
            if group == "_meta":
                continue
            f.write(f"[{group}]\n")
            for host in inventory[group]['hosts']:
                host_vars = inventory["_meta"]["hostvars"][host]
                line = (
                    f"{host} "
                    f"ansible_host={host_vars['ansible_host']} "
                    f"ansible_user={host_vars['ansible_user']} "
                    f"ansible_ssh_private_key_file={host_vars['ansible_ssh_private_key_file']}\n"
                )
                f.write(line)
            f.write("\n")

if __name__ == "__main__":
    inventory = get_instances()

    write_static_inventory_file(inventory)

    if len(sys.argv) == 2 and sys.argv[1] == "--list":
        print(json.dumps(inventory, indent=2))
    else:
        print("Inventory written to aws_inventory.ini")
        print("Hint: Use with Ansible like this:")
        print("  ansible-playbook playbook.yml -i aws_ec2_inventory.py")
