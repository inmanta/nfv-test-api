%define venv %{buildroot}/opt/%{name}
%define envdir /opt/%{name}
%define _p3 %{venv}/bin/python3

Name:           nfv-test-api
Version:        %{?pyversion}
Release:        1%{?dist}
Summary:        API server for testing virtual network setups

License:        Inmanta
URL:            https://github.com/inmanta/nfv-test-api
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  python3-pip

Requires:       python3
Requires:       bind-utils
Requires:       iperf3
Requires:       iproute


%description


%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{venv}

%{__python3} -m venv %{venv}


%{_p3} -m pip install -U wheel setuptools pip
%{_p3} -m pip install %{SOURCE0}
rm %{venv}/pip-selfcheck.json

# Use the correct python for bytecompiling
%define __python %{_p3}

# Fix shebang
sed -i "s|%{buildroot}||g" %{venv}/bin/*
find %{venv} -name RECORD | xargs sed -i "s|%{buildroot}||g"

mkdir -p %{buildroot}/etc
cp misc/config.yaml %{buildroot}/etc/nfv-test-api.yaml

# install helpers
mkdir -p %{buildroot}/etc/profile.d
install -p -m 644 misc/bash_rc %{buildroot}/etc/profile.d/nvf-test-api.sh
mkdir -p %{buildroot}%{_bindir}
install -p -m 755 misc/workon.sh %{buildroot}%{_bindir}/workon

# install unit files
mkdir -p  %{buildroot}%{_unitdir}
install -p -m 644 misc/iperf3.service %{buildroot}%{_unitdir}/
install -p -m 644 misc/nfv-test-api.service %{buildroot}%{_unitdir}/

%files
/etc
%{envdir}/bin
%{envdir}/lib
%{envdir}/lib64
%{envdir}/include
%{envdir}/pyvenv.cfg
%{_bindir}/workon
%{_unitdir}
#%config %attr(-, repomanager, repomanager) /etc/nfv-test-api.yaml

%post
%systemd_post nfv-test-api.service
%systemd_post iperf3.service

%preun
%systemd_preun nfv-test-api.service
%systemd_preun iperf3.service

%postun
%systemd_postun_with_restart nfv-test-api.service
%systemd_postun_with_restart iperf3.service

%changelog
* Fri Jun  9 2017 Bart Vanbrabant <bart.vanbrabant@inmanta.com>
- Initial package
