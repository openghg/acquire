# Installing an Acquire service

Here are instructions for setting up a server that can host
the Acquire services

## Step 1 - Set up a server

First, set up a server somewhere on the internet. For example,
on Oracle a VM.Standard2.1 would be fine. As a start, you need
the firewall to allow ingress to ports 22, 80, 443 and 8080.
Once SSL is working, we will close 8080...

## Step 2 - Install Fn pre-requisites

Fn requires Docker 17.10.0-ce or later. To install thisInstall this, e.g. on CentOS
using

```
$ sudo yum install -y yum-utils
$ sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
$ sudo yum install docker-ce docker-ce-cli containerd.io
```

Note that you may be prompted to accept a GPG key, if so, please check it matches the
key given at https://docs.docker.com/engine/install/centos/.

Now start docker and ensure it runs on login

```
$ sudo systemctl start docker
$ sudo systemctl enable docker
```

To test that Docker is functioning correctly run

```
$ sudo docker run hello-world
```

As Fn does not currently work with rootless docker we need to add our current user to the `docker` group.
Note that this does come with security implications which
are `outlined here <https://docs.docker.com/engine/security/#docker-daemon-attack-surface>`.

```
$ sudo usermod -aG docker $USER
```

## Step 3 - Install and start Fn

To install Fn we use a script provided by the Fn project. Instead of piping directly from curl we download
the script and check its hash before running it.

```
$ wget https://raw.githubusercontent.com/fnproject/cli/master/install
$ echo a02456b8c8aba8b727d35f704cbca9234e40d2731f200b94abeceb9467973a13 install | sha256sum -c
```

This should have printed `install: OK`. If not, check the bash script carefully.
We can now install Fn using the script.

```
$ sh install_fn.sh
```

We can now start Fn using

```
$ fn start
```

Check this has worked by navigating to `http://{IP_ADDRESS_OF_SERVER}:8080`

## Step 4 - Set up DNS and SSL

Optional - if you want to secure access to your service then you need
to create a DNS record for your service. First, create a DNS ANAME record
for the IP address of your server.

Next, install nginx as we will use this as the loadbalancer to handle
SSL.

```
$ sudo yum install nginx
$ sudo yum install certbot python2-certbot-nginx
$ sudo systemctl enable nginx
$ sudo systemctl start nginx
```

Now make sure that the local firewall allow http and https traffic

```
$ sudo systemctl enable firewalld
$ sudo firewall-cmd --zone=public --add-port=80/tcp
$ sudo firewall-cmd --zone=public --add-port=443/tcp
$ sudo firewall-cmd --zone=public --add-port=80/tcp --permanent
$ sudo firewall-cmd --zone=public --add-port=443/tcp --permanent
```

Navigate to `http://{IP_ADDRESS_OF_SERVER}` to see if you can see the
nginx launch page

Now get the SSL certificate

```
# sudo certbot --nginx -d {HOSTNAME}
```

Finally, you need to set up redirect to the Fn service. Do this by
editing your `/etc/nginx/nginx.conf` and making it equal

```
# For more information on configuration, see:
#   * Official English Documentation: http://nginx.org/en/docs/
#   * Official Russian Documentation: http://nginx.org/ru/docs/

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;

    server {
        listen       80 default_server;
        listen       [::]:80 default_server;
        server_name  _;
        root         /usr/share/nginx/html;

        # Load configuration files for the default server block.
        include /etc/nginx/default.d/*.conf;

        location / {
        }

        error_page 404 /404.html;
            location = /40x.html {
        }

        error_page 500 502 503 504 /50x.html;
            location = /50x.html {
        }
    }

    server {
    server_name hugs.acquire-aaai.com; # managed by Certbot
        root         /usr/share/nginx/html;

        # Load configuration files for the default server block.
        include /etc/nginx/default.d/*.conf;

        add_header 'Access-Control-Allow-Origin' '*';
        add_header 'Access-Control-Allow-Credentials' 'true';
        add_header 'Access-Control-Allow-Headers' 'Authorization,Accept,Origin,DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Content-Range,Range';
        add_header 'Access-Control-Allow-Methods' 'GET,POST,OPTIONS,PUT,DELETE,PATCH';

        location / {
        }

        location /t {
            proxy_pass http://127.0.0.1:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
        }

        error_page 404 /404.html;
            location = /40x.html {
        }

        error_page 500 502 503 504 /50x.html;
            location = /50x.html {
        }


    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/hugs.acquire-aaai.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/hugs.acquire-aaai.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}

    server {
    if ($host = hugs.acquire-aaai.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


        listen       80 ;
        listen       [::]:80 ;
    server_name hugs.acquire-aaai.com;
    return 404; # managed by Certbot


}}
```

And then, you may need to let SELinux know that you need to allow
nginx to route to Fn. You can check this by running;

```
$ sudo cat /var/log/audit/audit.log | grep nginx | grep denied | audit2allow -M mynginx
```

and follow the instructions recorded, e.g.

```
$ sudo semodule -i mynginx.pp
```

And allow the HTTP daemon network access

```
$ setsebool -P httpd_can_network_connect 1
```

## Step 5 - Clone Acquire

Once you have tested that Fn is accessible, then you can next install Acquire.

First, download via GitHub

```
$ git clone https://github.com/openghg/acquire
$ cd acquire
```

## Step 6 - Create users for each service

Make sure that you have created Oracle user accounts for each
service you want to install, with the ability to create object storage
buckets in your desired compartment. Also create a single bucket
for the service, e.g.

- user = acquire_identity
- compartment = acquire_services
- bucket = identity_bucket

## Step 7 - Create the `tenancy.json` file

In the `credentials` folder create a file called `tenancy.json` and fill in the tenancy ID and region for your tenancy

```
{
  "tenancy_OCID": "ocid1.tenancy.my-tenancy-id",
  "region": "eu-frankfurt-1"
}
```

## Step 8 - Setup the Fn functions

Run `setup_services.py` and ...

Press enter after each step...


### Set the hostname for the Acquire server

The first piece of information you will be asked for is the address of the Fn server. For our
Acquire functions we use `acquire.openghg.org`. You don't need to add http:// / https:// before
the hostname as this will be done for you.

```
Please enter the the hostname: acquire.openghg.org
```

## Step 8 - Create service secrets

Generate the encryption keys for each service using the `generate_keys.py` script in the `credentials` folder.

```
$ python generate_keys.py
```

This will generate a public/private keypair for each of the services listed in `services.json` and give each key a passphrase generated using `secrets.token_urlsafe`.

Make a note of the passphrases that are printed to screen. These will be required when we pass this secret data to the functions themselves.

## Step 8 - Upload keys to Oracle Cloud Interface

We will now upload each public key to its respective OCI user. To make the process easier a helper script `show_keys.py` will show the contents
of the public key for each service on screen. The script will run through the services in alphabetical order.

```
$ python show_keys.py

This will show the contents of the public key for each service for upload to the Oracle Cloud interface



--------------------------
Key for: access
--------------------------


-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA4C6ttyhAgVvlVtUVnQwB
24Bv3JvvhN2WX1y6LC+dl5UKlKXaO6UqJ5XU3u5wSXIFM+CbhhV6V/IL6EpNfiyb
1bEBzYbZJF7fwn6mqdZo2POozlS0qNN98ilyT+3Fni6YXMlOgPn4Cu8q/mm1Hxjt
+fP8mCOk0ubyELL7Ygp/Hlc8OhS87wmeLNdSVdPZ5O+hhi6QTxAyzP2JrlGVLSHg
q5ONCFIxLoQdp53Ot/NIzCYS8zGoBGnzDwGBCNkvmUrZX6wySoqORGbBaIjCfkaf
Sms5jj7cKZUrjPVQz0+6mR000EO1r9r1tqAK/OFVzvebPWI5wtCL9RqF7hC6qQT+
aVmjxT7dqJwb2jUKDn+j3uVqpJAnvWrwRr0VppHQXGc33Ypxceq2zBLwFUPO5dE2
WBV/CZ88BufNyv/mgXv7PMuwCF9sc7E8E9kYjrtwyvl3gO3QYnlLjzPyhEwDa6Zk
XN83hz8zrP4MNaWsWQ4TC2YfBWTfaU4gkdyxljB9mock7mXwQaYBLd+k9S5R1VB
2hH4Bu/icbczhbXCwUZcqDxaZxfMpN9wxYmXoES7mockdxKtZEULV644pxnczcCF
t6ISv8ccU7WL9iO611Dv/wvK5KONOZZkzibFgYpPmockqtDQ9RA+7jK3ni487AIF
1dMNfNJIAP66wXMRrWkPTR0CAwEAAQ==
-----END PUBLIC KEY-----



Press any key for the next service...
```

To upload the key go to the Oracle Cloud interface and go to `Identity` -> `Users`. There should be a user for each service (created in step 6). Click on the username and then go to `API Keys` in the `Resources` menu then `Add API Key` -> `Paste Public Key` and paste the contents of the key shown
by the script. Repeat this process for each service.

### Generate `secret_key` files

Now we will generate a `secret_key` file for each service. Each `secret_key` is a file with a 32-byte hexadecimal
token written to it.

```
$ python generate_secret_keys.py
```

### Pass secrets to Fn apps

With Acquire, each function resides in its own app (as Fn calls them). We now need to pass the secrets we've generated 
to each Fn app.

```
python credentials_to_fn.py
```

This will prompt the user to input each piece of data required 



where `{name}` is the name of the key (e.g. `acquire_identity`) and
`{passphrase}` is the passphrase you will use to protect this key.
Make a note of the passphrase as you will need it later.

This will create a public and private key used to log into the service.

Log onto the OCI console and upload the public key to the user account
on OCI that you have specified for this service. Make a record
of the fingerprint that OCI will report.

Next, create a Fn app for the service, e.g.

```
# fn create app identity
```

Next use `generate_secret_keys.py` to create a `secret_key` file for each of the services.
That script will print the generated passphrases to screen, make a note of these for the next
step.

Then, run `credentials_to_fn.py` and enter the requested information at each stage, this will include
the OCIDs of the OCI user, compartment, bucket and key fingerprint that will be used to
store data for this service.

You should see a lot printed to the screen, showing that an encrypted config
has been added for the service.

Next, you need to deploy the service. Do this by typing

```
# cd ..
# cd ../base_image
# ./build_and_push.sh
# cd -
# fn deploy . --local
```

Check that the service is working by navigating to
`http://{SERVER_IP}:8080/t/{SERVICE_NAME}`

(or, by calling `fn invoke {SERVICE} {SERVICE}-root`)
