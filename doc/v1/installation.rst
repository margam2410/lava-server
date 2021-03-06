.. _installation:

LAVA Installation
*****************

The default install provides an Apache2 config suitable for
a LAVA server at ``http://localhost/`` once enabled.

See :ref:`packaging_distribution` for more information or for
debugging.

.. _lava_requirements:

Requirements to Consider Before Installing LAVA
###############################################

Software Requirements
=====================

See :ref:`debian_installation` for instructions.

We currently recommend installing LAVA on `Debian`_ unstable, stretch
or jessie. Installations using jessie (the current Debian stable release)
should use updates available in ``jessie-backports``.

Contributions to support other distributions are welcome.

.. _Debian: http://www.debian.org/

If you'd like to help us with other distributions feel free to contact
us using the :ref:`lava_devel` mailing list.

.. note:: See :ref:`tftp_support` for changes in the :term:`tftp`
   software requirements after the **2015.8 release**.

Hardware Requirements
=====================

A small LAVA instance can be deployed on any modest hardware. We
recommend at least one 1GB of RAM for runtime activity (this is
shared, on a single host, among the database server, the application
server and the web server). For storage please reserve about 20GB for
application data, especially if you wish to mirror current public LAVA
instance used by Linaro.  LAVA uses append-only models so the storage
requirements will grow at about several GB a year.

A small LAVA instance can be deployed on reasonably modest hardware. [#f2]_
We recommend:

 * At least 1GB of RAM for runtime activity (this is shared, on a single
   host, among the database server, the application server and the web server)
 * At least 20GB of storage for application data, job log files etc. in
   addition to the space taken up by the operating system.

.. rubric:: Footnotes

.. [#f1] See the section :ref:`serial_connections` for details of
         configuring serial connections to devices
.. [#f2] If you are deploying many devices and expect to be running large
         numbers of jobs, you will obviously need more RAM and disk space

Device requirements
-------------------

Devices you wish to deploy in LAVA need to be:
 * Physically connected to the server via usb, usb-serial,
   or serial or
 * connected over the network via a serial console server or
 * a fastboot capable device accessible from the server or
 * an emulated virtual machines and/or simulators that allow a
   serial connection

Multi-Node hardware requirements
--------------------------------

If the instance is going to be sent any job submissions from third
parties or if your own job submissions are going to use Multi-Node,
there are additional considerations for hardware requirements.

Multi-Node is explicitly about synchronising test operations across
multiple boards and running Multi-Node jobs on a particular instance
will have implications for the workload of that instance. This can
become a particular problem if the instance is running on virtualised
hardware with shared I/O, a limited amount of RAM or a limited number
of available cores.

.. note:: Downloading, preparing and deploying test images can result
 in a lot of synchronous I/O and if this instance is running the server
 and the dispatcher, running synchronised Multi-Node jobs can cause the
 load on that machine to rise significantly, possibly causing the
 server to become unresponsive.

It is strongly recommended that Multi-Node instances use a separate
dispatcher running on non-virtualised hardware so that the (possibly
virtualised) server can continue to operate.

Also, consider the number of boards connected to any one dispatcher.
MultiNode jobs will commonly compress and decompress several test image
files of several hundred megabytes at precisely the same time. Even
with a powerful multi-core machine, this has been shown to cause
appreciable load. It is worth considering matching the number of boards
to the number of cores for parallel decompression and matching the
amount of available RAM to the number and size of test images which
are likely to be in use.

Which release to install
########################

LAVA makes regular monthly releases called ``production releases`` which
match the packages installed onto http://validation.linaro.org/. These
releases are also uploaded to Debian unstable and backports (see :ref:`debian_installation`).
Packages uploaded to Debian typically migrate automatically into the
current Ubuntu development release - at time of writing that is
Ubuntu Utopic Unicorn, scheduled for release as 14.10. ``production``
releases are tracked in the ``release`` branch of the upstream git
repositories.

Interim releases are made available from the the
:ref:`staging-repo <lava_repositories>`.

During periods when the internal transitions within Debian require that
``lava-server`` is unable to migrate into the testing suite, users
running Debian Jessie (testing) can obtain the same release using the
``people.linaro.org`` repository to provide packages which are not
present in Debian Jessie.

The ``lava-dev`` package includes scripts to assist in local developer
builds directly from local git working copies which allows for builds
using unreleased code, development code and patches under review.

If in doubt, install the ``production`` release of ``lava-server``
from official distribution mirrors. (Backports are included on Debian
mirrors.)

.. _install_types:

Installation Types
##################

.. _single_instance:

Single Master Instance installation
===================================

A single instance runs the web frontend, the database, the scheduler
and the dispatcher on a single machine. If this machine is also running
tests, the device (or devices) under test (:term:`DUT`) will also need
to be connected to this machine, possibly over the network, using
USB or using serial cables.

To install a single master instance and create a superuser, refer to
:ref:`debian_installation` installation.

The old `distributed_instance` installation method has been **deprecated**
as the :term:`refactoring` introduces a much improved architecture for
remote workers using `ZMQ`.

.. _pipeline_install:

What is the Pipeline?
=====================

.. note:: Linaro production systems in the Cambridge lab began to migrate to
   the pipeline with the 2016.2 production release whilst retaining support
   for the deprecated model until the migration is complete.
   Deprecated support is due to be removed in 2017.

In parallel with the **deprecated** :ref:`single_instance` and `distributed_instance`
models, the :term:`dispatcher refactoring <refactoring>` introduces changes and new
elements which should not be confused with the previous production models.
It is supported to install LAVA using solely the new design but there are some
considerations regarding your current device usage.
Submission requirements and device support can change before and during a
migration to the new design.

This documentation includes notes on the new design, so to make things
clearer, the following terms refer exclusively to the new design and
have no bearing on :ref:`single_instance` or :ref:`distributed_instance`
installation methods which are being used for current production instances
in the Cambridge lab.

#. :term:`pipeline`
#. :term:`refactoring`
#. `device dictionary`
#. `ZMQ`

The pipeline model also changes the way that results are gathered,
exported and queried, replacing the `bundle stream`,
`result bundle` and `filter` dashboard objects. This new
`results` functionality only operates on pipeline test jobs and is ongoing
development, so some features are incomplete and likely to change in future
releases. Admins can choose to not show the new results app, for example until
pipeline devices are supported on that instance, by setting the ``PIPELINE`` to
``false`` in :file:`/etc/lava-server/settings.conf` - make sure the file
validates as JSON before restarting apache::

 "PIPELINE": false

If the value is not set or set to ``true``, the Results app will be displayed.

A note on wsgi buffers
======================

When submitting a large amount of data to the django application,
it is possible to get an HTTP 500 internal server error. This problem
can be fixed by appending ``buffer-size = 65535`` to
``/etc/lava-server/uwsgi.ini``

Automated installation
======================

Using debconf pre-seeding
-------------------------

debconf can be easily automated with a text file which contains the
answers for debconf questions - just keep the file up to date if the
questions change. For example, to preseed a worker install::

 # cat preseed.txt
 lava-server   lava-worker/db-port string 5432
 lava-server   lava-worker/db-user string lava-server
 lava-server   lava-server/master boolean false
 lava-server   lava-worker/master-instance-name string default
 lava-server   lava-worker/db-server string snagglepuss.codehelp
 lava-server   lava-worker/db-pass string werewolves
 lava-server   lava-worker/db-name string lava-server

Insert the seeds into the debconf database::

 debconf-set-selections < preseed.txt

::

 # debconf-show lava-server
 * lava-worker/master-instance-name: default
 * lava-server/master: false
 * lava-worker/db-pass: werewolves
 * lava-worker/db-port: 5432
 * lava-worker/db-name: lava-server
 * lava-worker/db-server: snagglepuss.codehelp
 * lava-worker/db-user: lava-server

The strings available for seeding are in the Debian packaging for the
relevant package, in the ``debian/<PACKAGE>.templates`` file.

* http://www.debian-administration.org/articles/394
* http://www.fifi.org/doc/debconf-doc/tutorial.html

.. _user_authentication:

User authentication
===================

LAVA frontend is developed using Django_ web application framework
and user authentication and authorization is based on standard `Django
auth subsystems`_. This means that it is fairly easy to integrate authentication
against any source for which Django backend exists. Discussed below are
tested and supported authentication methods for LAVA.

.. _Django: https://www.djangoproject.com/
.. _`Django auth subsystems`: https://docs.djangoproject.com/en/dev/topics/auth/

.. note:: The previous OpenID support is not compatible with newer versions of django
   (versions 1.9 or later). OpenID is available in Debian Jessie but not in unstable or
   Stretch. If the ``python-django-auth-openid`` package is available and installed,
   OpenID support will be enabled, otherwise it will be omitted, automatically.

Local Django user accounts are supported. When using local Django
user accounts, new user accounts need to be created by Django admin prior
to use.

Support for `OAuth2`_ is under investigation in LAVA.

.. _OAuth2: http://oauth.net/2/

.. _launchpad_openid:

Using Launchpad OpenID
----------------------

LAVA server, by default, is preconfigured to authenticate using
Launchpad OpenID service but only **if** ``django-auth-openid`` support
is available, e.g. Debian Jessie. Newer versions of django cannot work
with the outdated django_openid_auth support.

Your chosen OpenID server is configured using the ``OPENID_SSO_SERVER_URL``
in ``/etc/lava-server/settings.conf`` (JSON syntax).

To use Launchpad even if the LAVA default changes, use::

 "OPENID_SSO_SERVER_URL": "https://login.ubuntu.com/",

Restart ``lava-server`` and ``apache2`` services if this is changed.

.. _google_openid:

Using Google+ OpenID
--------------------

Google+ OpenID also needs the ``python-django-auth-openid`` support
to be available.

To switch from Launchpad to Google+ OpenID, change the setting for the
``OPENID_SSO_SERVER_URL`` in ``/etc/lava-server/settings.conf``
(JSON syntax)::

 "OPENID_SSO_SERVER_URL": "https://www.google.com/accounts/o8/id",

The Google+ service is already deprecated and is due to be deactivated
in September 2014 in preference for OAuth2.

Restart ``lava-server`` and ``apache2`` services for the change to
take effect.

.. _ldap_authentication:

Using Lightweight Directory Access Protocol (LDAP)
--------------------------------------------------

LAVA server could be configured to authenticate via Lightweight
Directory Access Protocol ie., LDAP. LAVA uses `django_auth_ldap`_
backend for LDAP authentication.

.. _`django_auth_ldap`: http://www.pythonhosted.org/django-auth-ldap/

Your chosen LDAP server is configured using the following parameters
in ``/etc/lava-server/settings.conf`` (JSON syntax)::

  "AUTH_LDAP_SERVER_URI": "ldap://ldap.example.com",
  "AUTH_LDAP_BIND_DN": "",
  "AUTH_LDAP_BIND_PASSWORD": "",
  "AUTH_LDAP_USER_DN_TEMPLATE": "uid=%(user)s,ou=users,dc=example,dc=com",
  "AUTH_LDAP_USER_ATTR_MAP": {
    "first_name": "givenName",
    "email": "mail"
  },
  "DISABLE_OPENID_AUTH": true

.. note:: ``DISABLE_OPENID_AUTH`` should be set in order to remove
   OpenID based authentication support in the login page.

Use the following parameter to set a custom LDAP login page message::

    "LOGIN_MESSAGE_LDAP": "If your Linaro email is first.second@linaro.org then use first.second as your username"

Other supported parameters are::

  "AUTH_LDAP_GROUP_SEARCH": "ou=groups,dc=example,dc=com",
  "AUTH_LDAP_USER_FLAGS_BY_GROUP": {
    "is_active": "cn=active,ou=django,ou=groups,dc=example,dc=com",
    "is_staff": "cn=staff,ou=django,ou=groups,dc=example,dc=com",
    "is_superuser": "cn=superuser,ou=django,ou=groups,dc=example,dc=com"
  }

.. note:: Apart from the above supported parameters, in order to do
          more advanced configuration, make changes to
          ``/usr/lib/python2.7/dist-packages/lava_server/settings/common.py``

Restart ``lava-server`` and ``apache2`` services if this is changed.

LAVA server branding support
============================

The icon, link, alt text, bug URL and source code URL of the LAVA link on each
page can be changed in the settings ``/etc/lava-server/settings.conf`` (JSON syntax)::

   "BRANDING_URL": "http://www.example.org",
   "BRANDING_ALT": "Example site",
   "BRANDING_ICON": "https://www.example.org/logo/logo.png",
   "BRANDING_HEIGHT": 26,
   "BRANDING_WIDTH": 32,
   "BRANDING_BUG_URL": "http://bugs.example.org/lava",
   "BRANDING_SOURCE_URL": "https://github.com/example/lava-server",


If the icon is available under the django static files location, this location
can be specified instead of a URL::

   "BRANDING_ICON": "path/to/image.png",

There are limits to the size of the image, approximately 32x32 pixels, to avoid
overlap.

The ``favicon`` is configurable via the Apache configuration::

 Alias /favicon.ico /usr/share/lava-server/static/lava-server/images/linaro-sprinkles.png

LAVA Dispatcher network configuration
=====================================

``/etc/lava-dispatcher/lava-dispatcher.conf`` supports overriding the
``LAVA_SERVER_IP`` with the currently active IP address using a list of
network interfaces specified in the ``LAVA_NETWORK_IFACE`` instead of a
fixed IP address, e.g. for LAVA installations on laptops and other devices
which change network configuration between jobs. The interfaces in the
list should include the interface which a remote worker can use to
serve files to all devices connected to this worker.

.. _serial_connections:

Setting Up Serial Connections to LAVA Devices
=============================================

.. _ser2net:

Ser2net daemon
--------------

ser2net provides a way for a user to connect from a network connection
to a serial port, usually over telnet.

http://ser2net.sourceforge.net/

``ser2net`` is a dependency of ``lava-dispatcher``, so will be
installed automatically.

Example config (in /etc/ser2net.conf)::

 #port:connectiontype:idle_timeout:serial_device:baudrate databit parity stopbit
 7001:telnet:0:/dev/serial_port1:115200 8DATABITS NONE 1STOPBIT

.. note:: In the above example we have the idle_timeout as 0 which
          specifies a infinite idle_timeout value. 0 is the
          recommended value. If the user prefers to give a positive
          finite idle_timeout value, then there is a possibility that
          long running jobs may terminate due to inactivity on the
          serial connection.

StarTech rackmount usb
----------------------

W.I.P

* udev rules::

   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="ST167570", SYMLINK+="rack-usb02"
   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="ST167569", SYMLINK+="rack-usb01"
   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="ST167572", SYMLINK+="rack-usb04"
   SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="ST167571", SYMLINK+="rack-usb03"

This will create a symlink in /dev called rack-usb01 etc. which can then be addressed in the :ref:`ser2net` config file.

Contact and bug reports
=======================

Please report bugs using bugzilla:
https://bugs.linaro.org/enter_bug.cgi?product=LAVA%20Framework

You can also report bugs using ``reportbug`` and the
Debian Bug Tracking System: https://bugs.debian.org/cgi-bin/pkgreport.cgi?pkg=lava-server

Feel free to contact us at validation (at) linaro (dot) org and on
the ``#linaro-lava`` channel on OFTC.
