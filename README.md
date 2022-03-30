# vmware-scripts
Collection of various scripts for vSAN and vSphere.

## Script esxi/auto-create-logs.py
This script automatically creates an ESXi log bundle of the host it's running on and of the specified remote hosts when the specified log message in the specified log file is encountered.
Additionally, on the ESXi host the script is running on it can also create a hostd livedump if specified.

The script will also create a log file in the specified working directory: auto-create-logs.log
This log file will contain the start and completion times for the individual log bundle collections.

### Running the script in the background (so you can close the SSH session)
Add "setsid" at the start of the command and "&" at the end of it.

**Example:**
setsid python /tmp/auto-create-logs.py -m "mark: TEST" -f /var/log/vmkernel.log -w /vmfs/volumes/vsanDatastore/workDir/ -r somehost02.domain.com somehost03.domain.com -p "Password123" &

## Script vsan/get-unmap-stats.py
This script needs to be executed on a live ESXi host and will get the unmap stats for the vSAN objects and related VM names.

**Example:**
```
[root@someesxi01:~] python /tmp/get-unmap-stats.py
 Object UUID                          | Total number of unmaps | Total unmap bytes            | Related VM
------------------------------------------------------------------------------------------------------------------
 e6c15160-0427-e65d-fa9c-0cc47ac73060 |                 761909 |                 973444784128 | testVM01
 6ca40f61-3b8d-a57c-fa55-0cc47ac731c6 |                  16681 |                  50117963776 | testVM02
 c3efe15f-de83-729e-7b53-0cc47ac73060 |                      0 |                            0 | testVM03
 24232661-51d9-46a5-c9f7-0cc47ac73124 |                      0 |                            0 | VCSA70
 a1866e5d-366d-73b1-63bf-0cc47ac73060 |                      0 |                            0 | testVM04
 4c365260-ec2d-7bb6-06df-0cc47ac73124 |                      0 |                            0 | testVM05
 ```

## Script vsan/vsan-objects-overview.py
This script provides a summary of all objects in the vSAN cluster (e.g. component location, related VM name, object type, etc.).
For troubleshooting purposes the script can also just list components that are not in an active state, to more easily pinpoint were affected components are located, whether there's a common denominator (e.g. all on the same host / disk?), etc.

**Example:**
```
[root@mm-esxi01:~] /tmp/vsan-objects-overview.py
vSAN Object UUID                     | Object Type      | DOM Owner                | vSAN Component States                                           | Capacity Device with Component | Host with Component      | Related VM Name
-------------------------------------+------------------+--------------------------+-----------------------------------------------------------------+--------------------------------+--------------------------+---------------------------
6f5a9e60-fd4e-8b7a-c7e1-0050568ffcfb | VSWP             | mm-esxi04.csl.vmware.com | aed59861-bc72-7c8c-5555-0050568f9812 (Witness): Active          | mpx.vmhba2:C0:T1:L0:2          | mm-esxi05.csl.vmware.com | TestVM01
                                                                                   | aed59861-da78-788c-0ccc-0050568f9812 (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi04.csl.vmware.com |
                                                                                   | 6f5a9e60-1d40-2c7b-29f5-0050568ffcfb (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi01.csl.vmware.com |
-------------------------------------+------------------+--------------------------+-----------------------------------------------------------------+--------------------------------+--------------------------+---------------------------
76599e60-b0e9-1e00-b323-0050568ffcfb | Namespace        | mm-esxi05.csl.vmware.com | acd59861-250b-4e2b-8d1c-0050568f9812 (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi05.csl.vmware.com | TestVM01
                                                                                   | e7e59861-3f13-5d96-2e4d-0050568fdf72 (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi01.csl.vmware.com |
                                                                                   | 76599e60-ec0d-1401-e106-0050568ffcfb (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi01.csl.vmware.com |
                                                                                   | acd59861-4c36-522b-ca6d-0050568f9812 (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi02.csl.vmware.com |
-------------------------------------+------------------+--------------------------+-----------------------------------------------------------------+--------------------------------+--------------------------+---------------------------
7a599e60-b839-639a-970c-0050568ffcfb | VMDK             | mm-esxi05.csl.vmware.com | 7a599e60-17ab-329b-57a3-0050568ffcfb (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi05.csl.vmware.com | TestVM01
                                                                                   | c09b9c61-52ed-3f0f-e91f-0050568fdf72 (Witness): Active          | mpx.vmhba2:C0:T1:L0:2          | mm-esxi02.csl.vmware.com |
                                                                                   | 7a599e60-bb7a-359b-dad4-0050568ffcfb (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi01.csl.vmware.com |
-------------------------------------+------------------+--------------------------+-----------------------------------------------------------------+--------------------------------+--------------------------+---------------------------
dea69b60-4354-0277-5398-0050568f109a | Namespace        | mm-esxi04.csl.vmware.com | 58bc8c61-1bc9-3598-3cfd-0050568fc30e (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi04.csl.vmware.com | .vsan.stats
                                                                                   | dea69b60-632e-0478-9e5e-0050568f109a (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi01.csl.vmware.com |
                                                                                   | dea69b60-d794-0078-578a-0050568f109a (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi01.csl.vmware.com |
                                                                                   | a6d59861-82e9-7667-9cd5-0050568f9812 (Component): Active        | mpx.vmhba2:C0:T1:L0:2          | mm-esxi02.csl.vmware.com |
```

## Script vsan/vsan-unaligned-io.py
This script lists unaligned vSAN IO based on the vSAN traces in an ESXi log bundle. The output will also contain the latency for each unaligned IO.
Optionionally a graph can be plotted as well.
The vSAN trace files need to have the file ending of either .txt or .log and have to have been processed by vsanTraceReader before. To make things easier, you can use the script "process-vsan-traces.sh" from this repo.

**Dependencies on Python modules:**
- matplotlib
- numpy
- pandas
- seaborn
- vsancmmdsfunctions.py (in this repo)
- vsantracefunctions.py (in this repo)

## Script vsan/process-vsan-traces.sh
This script can be used to automatically extract all the vSAN traces in an ESXi log bundle and process them using vsanTraceReader.
Note: vSAN traces are written in binary and require to be processed by vsanTraceReader to make them human-readable.
