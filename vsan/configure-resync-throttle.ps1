# Author: Manuel Moser
# Version: 1.1

# Command-line parameters
Param(
	[Parameter(Mandatory=$true,Position=1)][string]$cluster,
	[Parameter(Mandatory=$true,Position=2)][string]$value,
	[Parameter(Mandatory=$false,Position=3)][string]$moid
)

$ErrorActionPreference = "Stop"

# Functions
Function Set-Resync-Throttle {
	$clusterMoid = (Get-Cluster -Name "$cluster").ExtensionData.MoRef

	if ($clusterMoid -eq $null -And $moid) {
		$clusterMoid = New-Object -Type VMware.Vim.ManagedObjectReference
		$clusterMoid.Type = ClusterComputeResource
		$clusterMoid.Value = $moid
	} elseif ($clusterMoid -eq $null) {
		Write-Host "Couldn't get MoRef via cluster ExtenstionData and no MoID was specified manually. Either try to update VMware PowerCLI or manually specify the cluster's MoID"
		Exit
	}
	
	$vsanConfigView = Get-VsanView -id "VsanVcClusterConfigSystem-vsan-cluster-config-system"
	$vsanConfigResults = $vsanConfigView.VsanClusterGetConfig($clusterMoid)
	
	$vsanReconfigSpec = New-Object -Type VMware.Vsan.Views.VimVsanReconfigSpec
	$vsanReconfigSpec.ResyncIopsLimitConfig = New-Object -Type VMware.Vsan.Views.ResyncIopsInfo
	$vsanReconfigSpec.ResyncIopsLimitConfig.ResyncIops = $value

	$vsanConfigView.VsanClusterReconfig($clusterMoid, $vsanReconfigSpec)
}

# Main
Set-Resync-Throttle