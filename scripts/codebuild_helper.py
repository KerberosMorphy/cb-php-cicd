import argparse
from subprocess import PIPE, Popen
from os import environ
from sys import exit

parser = argparse.ArgumentParser('CodeBuild Helper', description='Command executor for Code Build')

parser.add_argument('--registry_login', help='Docker Registry', action="store_true")
parser.add_argument('--build_docker', help='Build Docker', action="store_true")
parser.add_argument('--trigger_codebuild', help='Trigger CodeBuild', action="store_true")
parser.add_argument('-r', '--registry', type=str, help='Docker Registry', default="docker.io")
parser.add_argument('-u', '--username', type=str, help='Docker Username')
parser.add_argument('-w', '--password', type=str, help='Docker Username')
parser.add_argument('-i', '--image_name', type=str, help='Image Name')
parser.add_argument('-o', '--image_override', type=str, help='Image Override Name')
parser.add_argument('-p', '--project_name', type=str, help='Project Name')
parser.add_argument('-a', '--build_arg', type=str, help='Build Arg', default="")
parser.add_argument('-d', '--dockerfile', type=str, help='Dokerfile Name', default="Dockerfile")
parser.add_argument('-t', '--tags_list', type=str, nargs='*', help='Tags other than "latest"')

args = parser.parse_args()

def console_command(options: list, stdin=None):
    proc = Popen(options, stdin=PIPE, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    if input:
        return proc.communicate(input=stdin)
    else:
        return proc.communicate()

def set_error(code):
    console_command([f'FAIL=$(echo {code})'])

def error_handler(code):
    set_error(code)
    if code == "PRE_BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
        exit(1)
    elif code == "BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
        exit(1)
    elif code == "POST_BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
        exit(1)
    else:
        print('NO FAIL')

def registry_login(username, password, registry="docker.io"):
    print("")
    print("Login to docker")
    res, err = console_command(["docker", "login", "-u", username, "--password-stdin", registry], stdin=password)
    print(res)
    print(err)

def docker_exist(image):
    print("")
    print("Check if image exist")
    res, _ = console_command(["docker", "manifest", "inspect", image])
    if res:
        print("Image exist")
        return True
    print("Image doesn't exist")
    return False

def build_docker(image_name, tags_list=[], dockerfile="Dockerfile", build_arg=""):
    print("")
    tags_set = {"latest"}
    tags_set |= set(tags_list)
    tags = []
    for tag in list(tags_set):
        tags.append("--tag")
        tags.append(f"{image_name}:{tag}")
    print("Set registry image name to build...")
    print(f"Image name set to {image_name}")
    print(f"Dockerfile set to {dockerfile}")
    print("")
    print("Pull image from registry to by used as cache...")
    res, err = console_command(["docker", f"pull --quiet {image_name}:latest"])
    print(res)
    print("")
    if build_arg:
        print(f"Build image with args {build_arg} from pulled image cache and create {tags}...")
        res, err = console_command(["docker", "build", "--quiet", "--cache-from", f"{image_name}:latest", "--build-arg", build_arg, *tags, "--file", f"docker/{dockerfile}", "docker/"])
        print(res)
        if err:
            raise AssertionError(f"{err}")
    else:
        print(f"Build image from pulled image cache and create {tags}...")
        res, err = console_command(["docker", "build", "--quiet", "--cache-from", f"{image_name}:latest", *tags, "--file", f"docker/{dockerfile}", "docker/"])
        print(res)
        if err:
            raise AssertionError(f"{err}")
    print("")
    print("Push the tagged Docker images to the container registry..")
    for tag in tags:
        if tag != "--tag":
            print(f"PUSH: docker push {tag}")
            res, err = console_command(["docker", "push", tag])
            print(res)
            if err:
                raise AssertionError(f"{err}")
    print("")

def trigger_codebuild(project_name, image_override=""):
    print("")
    err = False
    if image_override:
        _, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name, "--image-override", image_override])
    else:
        _, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name])
    # print(_)
    if err:
        raise AssertionError(f"{err}")

if __name__ == '__main__':
    args = parser.parse_args()
    error_handler(environ.get("FAIL", "NO_ERROR"))
    if args.registry_login:
        try:
            registry_login(username=args.username, password=args.password, registry=args.registry)
        except AssertionError as err:
            print(err)
            environ['FAIL'] = 'PRE_BUILD'
    elif args.build_docker:
        try:
            if not docker_exist(image=args.image_name) or True:
                build_docker(image_name=args.image_name, tags_list=args.tags_list, dockerfile=args.dockerfile, build_arg=args.build_arg)
        except AssertionError as err:
            print(err)
            environ['FAIL'] = 'BUILD'
    elif args.trigger_codebuild:
        try:
            trigger_codebuild(project_name=args.project_name, image_override=args.image_override)
        except AssertionError as err:
            print(err)
            environ['FAIL'] = 'POST_BUILD'
    error_handler(environ.get("FAIL", "NO_ERROR"))
