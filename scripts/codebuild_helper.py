import argparse
from subprocess import PIPE, Popen
from os import environ

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

def console_command(options: list, timeout=10):
    # TODO Faire une fonction utils qui gere les erreurs
    proc = Popen(options, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    return proc.communicate(timeout=timeout)

def error_handler(code):
    if code == "PRE_BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
    elif code == "BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
    elif code == "POST_BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")

def registry_login(username, password, registry="docker.io"):
    print("Login to docker")
    try:
        res, err = console_command(["echo", password, "|", "docker", "login", "-u", username, "--password-stdin", registry])
        if err:
            raise AssertionError(f"{err}")
        print("Login Success")
        print(res)
    except AssertionError as err:
        print("Login Failed")
        print(err)
    print("")

def build_docker(image_name, tags_list=[], dockerfile="Dockerfile", build_arg=""):
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
    try:
        res, err = console_command(["docker", "pull", "--quiet", f"{image_name}:latest", "||", "true"])
        if err:
            raise AssertionError(f"{err}")
        print("")
        if build_arg:
            print(f"Build image with args {build_arg} from pulled image cache and create {tags}...")
            res, err = console_command(["docker", "build", "--quiet", "--cache-from", f"{image_name}:latest", "--build-arg", build_arg, *tags, "--file", f"docker/{dockerfile}", "docker/"])
            if err:
                raise AssertionError(f"{err}")
        else:
            print(f"Build image from pulled image cache and create {tags}...")
            res, err = console_command(["docker", "build", "--quiet", "--cache-from", f"{image_name}:latest", *tags, "--file", f"docker/{dockerfile}", "docker/"])
            if err:
                raise AssertionError(f"{err}")
        print("")
        print("Push the tagged Docker images to the container registry..")
        for tag in tags:
            if tag != "--tag":
                res, err = console_command(["docker", "push", tag])
                if err:
                    raise AssertionError(f"{err}")
    except AssertionError as err:
        print("Push Failed")
        print(err)
        environ["FAIL"] = "BUILD"
    print("")

def trigger_codebuild(project_name, image_override=""):
    error_handler(environ.get("FAIL", "NO_ERROR"))
    try:
        err = False
        if image_override:
            res, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name, "--image-override", image_override])
        else:
            res, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name])
        if err:
            raise AssertionError(f"{err}")
    except AssertionError as err:
        print("Trigger Failed")
    error_handler(environ.get("FAIL", "NO_ERROR"))

if __name__ == '__main__':
    args = parser.parse_args()
    if args.registry_login:
        registry_login(username=args.username, password=args.password, registry=args.registry)
    elif args.build_docker:
        build_docker(image_name=args.image_name, tags_list=args.tags_list, dockerfile=args.dockerfile, build_arg=args.build_arg)
    elif args.trigger_codebuild:
        trigger_codebuild(project_name=args.project_name, image_override=args.image_override)
