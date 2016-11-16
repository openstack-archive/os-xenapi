======================
 Enabling in Devstack
======================

1. Download DevStack

2. Add this repo as an external repository::

     local.conf
     [[local|localrc]]
     enable_plugin os-xenapi https://github.com/openstack/os-xenapi.git [GITREF]

3. run ``stack.sh``
