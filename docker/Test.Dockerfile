ARG base_image=php:7.4

FROM ${base_image}

RUN set -xe

# Install git (the php image doesn't have it) which is required by composer
RUN apt-get update -yqq
RUN apt-get install git -yqq
RUN apt-get install python3.8 -yqq

# Install phpunit, the tool that we will use for testing
RUN curl --location --output /usr/local/bin/phpunit https://phar.phpunit.de/phpunit.phar
RUN chmod +x /usr/local/bin/phpunit

# Install mysql driver
# Here you can install any other extension that you need
# `docker-php-ext-install` is a script provided by the official PHP Docker image
# that you can use to easily install extensions. 
# For more information read the documentation at https://hub.docker.com/_/php
RUN docker-php-ext-install pdo_mysql
