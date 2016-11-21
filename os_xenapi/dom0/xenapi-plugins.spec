Name:           xenapi-plugins
Version:        %{version}
Release:        1
Summary:        Files for XenAPI support.
License:        ASL 2.0
Group:          Applications/Utilities
Source0:        xenapi-plugins-%{version}.tar.gz
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

%define debug_package %{nil}

%description
This package contains files that are required for XenAPI support for OpenStack.

%prep
%setup -q -n xenapi-plugins

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
if ! [ -d "$sr_mount_dir" ]; then
    echo "Cannot find the folder that sr mount" >&2
    exit 0
fi

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

%files
%defattr(-,root,root,-)
/etc/xapi.d/plugins/*
