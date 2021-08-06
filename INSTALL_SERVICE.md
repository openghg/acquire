# Installing an Acquire service

Here are instructions for setting up a server that can host
the Acquire services

## Step 1 - Set up a server

First, set up a server somewhere on the internet. For example,
on Oracle a VM.Standard2.1 would be fine. As a start, you need
the firewall to allow ingress to ports 22, 80, 443 and 8080.
Once SSL is working, we will close 8080...

## Step 2 - Install Fn pre-requisites

Fn requires Docker 17.10.0-ce or later. In this documentation we use a VM running CentOS 8, for other 
distributions please check https://docs.docker.com/engine/install/.

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

## Step 4 - Set up NGINX + get a LetsEncrypt certificate

Optional - if you want to secure access to your service then you need
to create a DNS record for your service. First, create a DNS ANAME record
for the IP address of your server.

Next, install nginx as we will use this as the loadbalancer to handle
SSL.

```
$ sudo yum install nginx
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

### Update NGINX configuration

Now we need to update the NGINX configuration files



### Install Certbot

Now we need to install `certbot` to get the certificate for us

```
$ sudo yum install epel-release
$ sudo yum install certbot python3-certbot-nginx
```

Now we can get the certificate

```
$ sudo certbot --nginx -d fn.openghg.org
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

## Step 5 - Create users for each service

Make sure that you have created Oracle user accounts for each
service you want to install, with the ability to create object storage
buckets in your desired compartment. Also create a single bucket
for the service, e.g.

- user = acquire_identity
- compartment = acquire_services
- bucket = identity_bucket

## Step 6 - Clone Acquire

Once you have tested that Fn is accessible, then you can next install Acquire.

First, download via GitHub

```
$ git clone https://github.com/openghg/acquire.git
$ cd acquire
```

## Step 7 - Create the `tenancy.json` file

In the `credentials` folder create a file called `tenancy.json` and fill in the tenancy ID and region for your tenancy

```
{
  "tenancy_OCID": "ocid1.tenancy.my-tenancy-id",
  "region": "eu-frankfurt-1"
}
```

# Step 8 - Setup the Fn functions

To setup the `Fn` functions we'll use the `setup_functions.py` script in the `credentials` folder. This script has some arguments you can pass to it.

```
$ python setup_functions.py -h
usage: setup_functions.py [-h] [--ci] [--save] [--load]

optional arguments:
  -h, --help  show this help message and exit
  --ci        create mock credentials for testing services with CI pipeline
  --save      save the configuration to file
  --load      load a previously created configuration
```

We will use the `--save` argument so that our configuration is saved to a `saved_config.json` file in the `credentials` folder.
To start the setup of the functions run the script and follow the steps below.

```
$ python setup_functions.py --save
```

### Set the hostname for the Acquire server

The first piece of information you will be asked for is the address of the Fn server. For our
Acquire functions we use `acquire.openghg.org`. You don't need to add http:// / https:// before
the hostname as this will be done for you.

```
Please enter the the hostname: acquire.openghg.org
```

### Enter the user OCID

You will then be asked for the OCID of the user for each service that you created in step 6.

```
We are now setting up the *** access *** service

Enter the user OCID:
```

### Key creation

The script next creates an RSA keypair in the service folder. The private key will be given a passphrase that is stored by the script and later passed into Fn. We will take the public key and upload it to the Oracle Cloud Interface.

### Uploading the public key

Next, the script will print an RSA public key for you to paste into the `API Keys` section for the user. To upload the key go to the Oracle Cloud interface and go to `Identity` -> `Users`. There should be a user for each service (created in step 6). Click on the username and then go to `API Keys` in the `Resources` menu then `Add API Key` -> `Paste Public Key` and paste the contents of the key shown. Only copy the key itself, an example is shown below.

```
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAqvD9zH89Ka+aHXKBpVoA
976c1yJ909dNbN9klu8kt2hVk7amUNA3O9CcJIC6F/gV9x7WFYDU1dVn/u31D1VZ
LZmfhCBp9xgMhpU5k8nhfJ7hl9Ix14CKNhEshhkn44Fw7/dmFIsCbJMiyaMoC0cG
Q7wyRBV/Y0ugqxJnbE7gHn6Y+8N4wPs5hJarLkPCs2v/ATgI5DeLUaeSBxjr1V/Z
Tb2fwPdUdXVuywdiMt46DqkrrXPrnxAVfm+kZOZetONE/wSBZpjYB/nndBt85auU
HR8GcPwxmRNNzjwAdnQ19kTd0X8QZx23hIQl3rnaHQfN90/RugGdEDYcOiM7Wxpc
ua842Y8+WBsMtDKiae8/X9zktwqMQDQaYh8g0O/JvWD7eS/RLi01+6HDSB2zksM2
PUoDdV2pPuqztaqIFV9/NR5RpffRoZm2eN1V9oIYkWBGo+HqZAtF6NogNhLxeUgq
6StGsrxnzBEK61LB8GTBfsXSVfIiwvFOGO5tNWA2YiMVZW0oz2WjCmjsuiR6/TvU
oF5Bh1vC7dvsMcDgUKeB2ABgPslXbbA+f1Lvrmv8fghGiIZaCGlE7S/+3eAqO/VL
EmZ/SchUv7l764Uuo4UvD10gXw0Clmc1xxvr677Rh+Dl0G+Wgcv9SpAWzj9gkm8q
BBKvzytyClH0yWWhQm2hYskCAwEAAQ==
-----END PUBLIC KEY-----
```

Then press enter to move onto the next step.

### Confirm the fingerprint

The OCI will then give us the fingeprint of the key, this will be in the format `b0:d4:b8:58:97:ff:d9:a6:db:63:00:a5:54:89:e3:94` but yours will differ from the one shown here. Copy the fingerprint given by OCI and paste it in for checking by the script.

### Passing data to Fn

After you've confirmed the fingerprint the script will create a file called `secret_key` in the service directory. This contains a password which will be used to encrypt the data that is passed to Fn.

> **_NOTE:_** The `secret_key` files and private keys (`<service_name>.pem`) files should never leave the server on which they are located.

You should see a lot printed to the screen, showing that an encrypted config has been added for the service.

Repeat this process for each service.

## Step 9 - Deploy the services

Next, you need to deploy the services. Do this changing to the `services` folder and running the `deploy_all.sh` script.

```
$ cd ../services
$ bash ./deploy_all.sh
```

You should see quite a lot printed to screen as the Docker images are build and deployed.

## Step 10 - Check the setup

Check that the service is working by navigating to `http://{SERVER_IP}:8080/t/{SERVICE_NAME}` 
(or, by calling `fn invoke {SERVICE} {SERVICE}-root`)
