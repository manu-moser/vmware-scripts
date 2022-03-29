# vmware-scripts
Collection of various scripts for vSAN and vSphere.

## Script get-unmap-stats.py
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

## Script vsan-unaligned-io.py
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

## Script process-vsan-traces.sh
This script can be used to automatically extract all the vSAN traces in an ESXi log bundle and process them using vsanTraceReader.
Note: vSAN traces are written in binary and require to be processed by vsanTraceReader to make them human-readable.
