===============================
os-xenapi
===============================

XenAPI library for OpenStack projects

Please fill here a long description which must be at least 3 lines wrapped on
80 cols, so that distribution package maintainers can use it in their packages.
Note that this is a hard requirement.

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/os-xenapi
* Source: http://git.openstack.org/cgit/openstack/os-xenapi
* Bugs: http://bugs.launchpad.net/os-xenapi

Features
--------

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Install Devstack on XenServer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Getting Started With XenServer and Devstack
____________________________________________

The purpose of the code in this directory is to help developers bootstrap a
XenServer(7.0 and above) + OpenStack development
environment. This file gives some pointers on how to get started.

Xenserver is a Type 1 hypervisor, so it is best installed on bare metal.  The
OpenStack services are configured to run within a virtual machine (called OS
domU) on the XenServer host. The VM uses the XAPI toolstack to communicate with
the host over a network connection (see `MGT_BRIDGE_OR_NET_NAME`).

The provided local.conf helps to build a basic devstack environment.

Introduction
................

Requirements
******************

 - An internet-enabled network with a DHCP server on it
 - XenServer box plugged in to the same network

This network will be used as the OpenStack management network. The VM Network
and the Public Network will not be connected to any physical interfaces, only
new virtual networks will be created by the `install_on_xen_host.sh` script.

Steps to follow
*********************

Yous should install a XenServer host at first, then you can launch the devstack installation through two ways,
 - On a remote linux client

  - Download install-devstack-xen.sh to the linux client
  - Configure the local.conf contents in install-devstack-xen.sh.
  - Generate passwordless ssh key using "ssh-keygen -t rsa -N "" -f devstack_key.priv"
  - Launch script using "install-devstack-xen.sh XENSERVER mypassword devstack_key.priv" with some optional arguments

 - On the XenServer host
   - Download os-xenapi to XenServer
   - Customise `local.conf`
   - Start `install_on_xen_host.sh` script

Brief explanation
***********************

The `install-devstack-xen.sh` script will:

 - Logon the XenServer host
 - Download os-xenapi folder to XenServer host
 - Generate local.conf file
 - Call install_on_xen_host.sh to do devstack installation
 - Do tempest test if required

The 'install_on_xen_host.sh' script will:

 - Verify the host configuration
 - Create template for devstack DomU VM if needed. Include:

  - Create the named networks, if they don't exist
  - Preseed-Netinstall an Ubuntu Virtual Machine , with 1 network interface:

   - `eth0` - Connected to `UBUNTU_INST_BRIDGE_OR_NET_NAME`, defaults to
     `MGT_BRIDGE_OR_NET_NAME`

  - After the Ubuntu install process finished, the network configuration is
    modified to:

   - `eth0` - Management interface, connected to `MGT_BRIDGE_OR_NET_NAME`. XAPI must be accessible through this network.
   - `eth1` - VM interface, connected to `VM_BRIDGE_OR_NET_NAME`
   - `eth2` - Public interface, connected to `PUB_BRIDGE_OR_NET_NAME`

 - Create a template of the VM and destroy the current VM
 - Create DomU VM according to the template and ssh to the VM
 - Create a linux service to enable devstack service after VM reboot. The service will:

  - Download devstack source code if needed
  - Call unstack.sh and stack.sh to install devstack

 - Reboot DomU VM

Step 1: Install Xenserver
.............................
Install XenServer on a clean box. You can download the latest XenServer for
free from: http://www.xenserver.org/

The XenServer IP configuration depends on your local network setup. If you are
using dhcp, make a reservation for XenServer, so its IP address won't change
over time. Make a note of the XenServer's IP address, as it has to be specified
in `local.conf`. The other option is to manually specify the IP setup for the
XenServer box. Please make sure, that a gateway and a nameserver is configured,
as `install-devstack-xen.sh` will connect to github.com to get source-code snapshots.

Step 2: Download install-devstack-xen.sh
.........................................
On your remote linux client, get the install scrpt under https://raw.githubusercontent.com/openstack/os-xenapi/master/tools/install-devstack-xen.sh

Step 3: Configure your local.conf contents inside the install-devstack-xen.sh
..............................................................................
Devstack uses a local.conf for user-specific configuration. Find below codes in install-devstack-xen.sh,

local.conf sample::

    [[local|localrc]]

    enable_plugin os-xenapi https://github.com/openstack/os-xenapi.git

    # Passwords
    MYSQL_PASSWORD=citrix
    SERVICE_TOKEN=citrix
    ADMIN_PASSWORD=citrix
    SERVICE_PASSWORD=citrix
    RABBIT_PASSWORD=citrix
    GUEST_PASSWORD=citrix
    XENAPI_PASSWORD="$XENSERVER_PASS"
    SWIFT_HASH="66a3d6b56c1f479c8b4e70ab5c2000f5"

    # Do not use secure delete
    CINDER_SECURE_DELETE=False

    # Compute settings
    VIRT_DRIVER=xenserver

    # Tempest settings
    TERMINATE_TIMEOUT=90
    BUILD_TIMEOUT=600

    # DevStack settings

    LOGDIR=${LOGDIR}
    LOGFILE=${LOGDIR}/stack.log

    # Turn on verbosity (password input does not work otherwise)
    VERBOSE=True

    # XenAPI specific
    XENAPI_CONNECTION_URL="http://$XENSERVER_IP"
    VNCSERVER_PROXYCLIENT_ADDRESS="$XENSERVER_IP"

    # Neutron specific part
    ENABLED_SERVICES+=neutron,q-domua
    Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch

    Q_ML2_PLUGIN_TYPE_DRIVERS=vlan,flat
    ENABLE_TENANT_TUNNELS=False
    ENABLE_TENANT_VLANS=True
    Q_ML2_TENANT_NETWORK_TYPE=vlan
    ML2_VLAN_RANGES="physnet1:1100:1200"

    SUBNETPOOL_PREFIX_V4=192.168.10.0/24
    NETWORK_GATEWAY=192.168.10.1

    VLAN_INTERFACE=eth1
    PUBLIC_INTERFACE=eth2

    # Nova user specific configuration
    # --------------------------------
    [[post-config|\\\$NOVA_CONF]]


Step 4: Run `./install-devstack-xen.sh` on your remote linux client
....................................................................
An example::
  # Create a passwordless ssh key
  ssh-keygen -t rsa -N "" -f devstack_key.priv
  # Install devstack
  ./install-devstack-xen.sh XENSERVER mypassword devstack_key.priv

If you don't select wait till launch(using "-w 0" option), once this script finishes executing, log into the VM (openstack domU) that it installed and tail the /opt/stack/devstack_logs/stack.log file. You will need to wait until it stack.log has finished executing.

Appendix
_________

This section contains useful information for running devstack in CI
environments / using ubuntu network mirrors.

Use a specific Ubuntu mirror for installation(only works when you select
.........................................................................
launch install scripts on the XenServer host)
................................................
To speed up the Ubuntu installation, you can use a specific mirror. To specify
a mirror explicitly, include the following settings in your `xenrc` file:

sample code::

    UBUNTU_INST_HTTP_HOSTNAME="archive.ubuntu.com"
    UBUNTU_INST_HTTP_DIRECTORY="/ubuntu"

These variables set the `mirror/http/hostname` and `mirror/http/directory`
settings in the ubuntu preseed file. The minimal ubuntu VM will use the
specified parameters.

Use an http proxy to speed up Ubuntu installation(only works when you select
.............................................................................
launch install scripts on the XenServer host)
..............................................

To further speed up the Ubuntu VM and package installation, an internal http
proxy could be used. `squid-deb-proxy` has prooven to be stable. To use an http
proxy, specify:

sample code::

    UBUNTU_INST_HTTP_PROXY="http://ubuntu-proxy.somedomain.com:8000"

in your `xenrc` file.

Export the Ubuntu VM to an XVA
************************************

Given you have an nfs export `TEMPLATE_NFS_DIR`:

sample code::

    TEMPLATE_FILENAME=devstack-jeos.xva
    TEMPLATE_NAME=jeos_template_for_ubuntu
    mountdir=$(mktemp -d)
    mount -t nfs "$TEMPLATE_NFS_DIR" "$mountdir"
    VM="$(xe template-list name-label="$TEMPLATE_NAME" --minimal)"
    xe template-export template-uuid=$VM filename="$mountdir/$TEMPLATE_FILENAME"
    umount "$mountdir"
    rm -rf "$mountdir"

Import the Ubuntu VM
**************************

Given you have an nfs export `TEMPLATE_NFS_DIR` where you exported the Ubuntu
VM as `TEMPLATE_FILENAME`:

sample code::

    mountdir=$(mktemp -d)
    mount -t nfs "$TEMPLATE_NFS_DIR" "$mountdir"
    xe vm-import filename="$mountdir/$TEMPLATE_FILENAME"
    umount "$mountdir"
    rm -rf "$mountdir"
