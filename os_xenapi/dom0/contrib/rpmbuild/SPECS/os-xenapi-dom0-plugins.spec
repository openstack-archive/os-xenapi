Name:           os-xenapi-dom0-plugins
Version:        %{version}
Release:        1
Summary:        Files for XenAPI support.
License:        ASL 2.0
Group:          Applications/Utilities
Source0:        os-xenapi-dom0-plugins.tar.gz
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%define debug_package %{nil}

%description
This package contains files that are required for XenAPI support for OpenStack.

%prep
%setup -q -n os-xenapi-dom0-plugins

%install
rm -rf $RPM_BUILD_ROOT
mkdir -p $RPM_BUILD_ROOT/etc
rsync -avz --exclude '*.pyc' --exclude '*.pyo' xapi.d $RPM_BUILD_ROOT/etc
chmod a+x $RPM_BUILD_ROOT/etc/xapi.d/plugins/*

%clean
rm -rf $RPM_BUILD_ROOT

%post
set -eu
default_sr="$(xe pool-list params=default-SR minimal=true)"
if [ -z "$default_sr" ]; then
    echo "Failed to get the default SR" >&2
    exit 1
fi
sr_mount_dir="/var/run/sr-mount/$default_sr"

if ! [ -d /images ]; then
    os_images_dir="$sr_mount_dir/os-images"

    echo "Creating /images" >&2
    if ! [ -d "$os_images_dir" ]; then
        echo "Creating $os_images_dir" >&2
        mkdir -p "$os_images_dir"
    fi

    echo "Setting up symlink: /images -> $os_images_dir" >&2
    ln -s "$os_images_dir" /images
fi

images_dev=$(stat -c %d "/images/")
sr_dev=$(stat -c %d "$sr_mount_dir/")

if [ "$images_dev" != "$sr_dev" ]; then
    echo "ERROR: /images/ and the default SR are on different devices"
    exit 1
fi

if ! [ -d /root/.ssh ]; then
    mkdir /root/.ssh
    chmod 0755 /root/.ssh
fi

if ! [ -e /root/.ssh/id_rsa ]; then
    if [ -e /root/.ssh/id_rsa.pub ]; then
        echo "ERROR: No private key, but public key exists" >&2
        exit 1
    fi

    echo "Generating a new rsa keypair for root" >&2
    ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
fi

if ! [ -e /root/.ssh/id_rsa.pub ]; then
    ssh-keygen -y -f /root/.ssh/id_rsa > /root/.ssh/id_rsa.pub
fi

if [ -e /root/.ssh/authorized_keys ] && grep -qf /root/.ssh/id_rsa.pub /root/.ssh/authorized_keys; then
    echo "Key already authenticated" >&2
else
    echo "Autenticating root's key" >&2
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
fi

if ssh -o StrictHostKeyChecking=no -o BatchMode=yes root@localhost true; then
    echo "Trust relation working" >&2
else
    echo "ERROR: ssh connection failed" >&2
    exit 1
fi

cat >> /root/.ssh/authorized_keys << ADDITIONAL_SSH_KEYS
ADDITIONAL_SSH_KEYS

%files
%defattr(-,root,root,-)
/etc/xapi.d/plugins/*