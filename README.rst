=========
os-xenapi
=========

XenAPI library for OpenStack projects

This library provides the support functions needed to connect to and manage a XenAPI-based
hypervisor, such as Citrix's XenServer.

* Free software: Apache license
* Source: http://git.openstack.org/cgit/openstack/os-xenapi
* Bugs: http://bugs.launchpad.net/os-xenapi
* Install Devstack on XenServer: https://github.com/openstack/os-xenapi/blob/master/tools/README.rst

Features
--------

The following features are supported since 0.3.1:

* VDI streaming
  It will allow the library user to create XenServer VDI from a gzipped
  image data stream; or create gzipped image data stream from a specified
  XenServer VDI. By comparing to the existing dom0 glance plugin, the
  image data gets processed on the fly via streams. So it doesn't create
  intermediate files. And it completely uses the formal VDI import or
  export APIs when it exchanges VDI data with XenServer.

* XAPI pool
  With this feature, we can deploy OpenStack on hosts which belong to a
  XAPI pool, so that we can get the benefits from XAPI pool features:
  e.g. it's able to live migrate instance between two hosts without
  moving the disks on shared storage.

The following features are supported since 0.3.2:

* Bootstrap compute node via a single command
  Now we can support to boostrap an OpenStack compute node by running the
  command of ``xenapi_bootstrap`` from a VM which is running on XenServer.
  At the moment, only CentOS 7.x is supported.
