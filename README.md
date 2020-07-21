# AWS CodeBuild

Explication de l'expérimentation d'un pipeline de déploiement avec GitHub Action.
L'utilisation de PHP est uniquement pour la démonstration,
les concepts peuvent être appliqués à n'importe quel langage.
Des éléments seront sautés puisque déjà abordés dans les exemples avec **GitHub**, **Bitbucket** et **GitLab**.

## Sections

- [**Configuration**](##configuration)
- [**Python**](##python)
- [`Test.Dockerfile`](##test.dockerfile)
- [**Build** `build-buildspec.yml`](##build)
- [**Test** `test-buildspec.yml`](##test)
- [**ChatOps** `chatops-buildspec.yml`](##chatops)
- [**Deploy** `deploy-buildspec.yml`](##deploy)

## Configuration

CodePipeline étant encore plus rigide que CodeBuild, j'ai privilégié l'utilisation unique de CodeBuild pour créer un Pipeline. Chaque CodeBuild déclenche l'étape suivante si réussi.

### Policies

Pour permettre le déclenchement de CodeBuild depuis un script CodeBuild il est important d'ajouter les permissions adéquates. Il faut donc autoriser `codebuild:StartBuild` sur la ressource représentant l'étape qui sera déclenché.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                ...
                "codebuild:StartBuild",
                ...
            ],
            "Resource": [
                ...
                "arn:aws:codebuild:ca-central-1:123412341234:project/NOM_DU_PROJET_CODEBUILD_A_DÉMARRER",
                ...
            ]
        },
        ...
    ]
}
```

Des informations confidentiels étant stocké dans **AWS Systems Manager** via les *Parameter Store*, il faut aussi autoriser leur accès dans les *Policies* via `ssm:GetParameters` sur les ressources représentant les *Parameter Store*.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                ...
                "ssm:GetParameters",
                ...
            ],
            "Resource": [
                ...
                "arn:aws:ssm:ca-central-1:123412341234:parameter/DOCKER_USERNAME",
                "arn:aws:ssm:ca-central-1:123412341234:parameter/DOCKER_PASSWORD",
                ...
            ]
        },
        ...
    ]
}
```

### Variables d'environnements

J'ai utilisé 2 types de variables d'environnements, les `parameter-store` et les `variables`.

Les `parameter-store` assigne à notre variable la valeur provenant de **AWS Systems Manager** via les *Parameter Store*.

```yml
env:
  parameter-store:
    DOCKER_USERNAME: DOCKER_USERNAME
    DOCKER_PASSWORD: DOCKER_PASSWORD
    NOM_DE_NOTRE_VARIABLE: NOM_DE_NOTRE_PARAMETER_STORE_DANS_AWS_SSM
  ...
```

À noter que je n'ai pas respecté la bonne pratique pour nommer mes `parameters-store`, une bonne nomenclature aurait probablement ressemblé à `/Client/Projet/Environnement/<Autre>/Docker/Username`.

```yml
DOCKER_USERNAME: /TM/PHPCICD/Prod/Docker/Username
DOCKER_PASSWORD: /TM/PHPCICD/Prod/Docker/Password
```

Autre type de variable utilisé sont les variables *"standard"* sont Clef/Valeur.

```yml
env:
  ...
  variables:
    DOCKER_REGISTRY: "docker.io"
    PHP_IMAGE: cb-php
    PHP_TEST_IMAGE: cb-php-test
    TEST_JOB_NAME: TEST-PHP-CICD
```

## Python

Pour ce cas d'utilisation j'ai privilégié **Python** au lieu de **bash** pour exécuter mes commandes. **Python** offre un langage plus lisible et plus facile à travailler.

Pour ne pas avoir à installer de module additionnel j'utilise le module `subprocess` de la librairie standard pour exécuter les commandes directement dans un terminale depuis **Python** grâce à la fonction `console_command`.

```python
def console_command(options: list, stdin=None):
    proc = Popen(options, stdin=PIPE, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    if stdin:
        return proc.communicate(input=stdin)
    else:
        return proc.communicate()
```

J'ai aussi généré un analyseur de commande simple pour choisir quel fonction python exécuté.

```sh
usage: CodeBuild Helper [-h] [--registry_login] [--build_docker] [--trigger_codebuild]
                        [-r REGISTRY] [-u USERNAME] [-w PASSWORD] [-i IMAGE_NAME]
                        [-o IMAGE_OVERRIDE] [-p PROJECT_NAME] [-a BUILD_ARG] [-d DOCKERFILE]
                        [-t [TAGS_LIST [TAGS_LIST ...]]]

Command executor for Code Build

optional arguments:
  -h, --help            show this help message and exit
  --registry_login      Login to Docker Registry
  --build_docker        Build Dockerfile ans Publish
  --trigger_codebuild   Trigger CodeBuild next step
  -r REGISTRY, --registry REGISTRY
                        Docker Registry
  -u USERNAME, --username USERNAME
                        Docker Username
  -w PASSWORD, --password PASSWORD
                        Docker Username
  -i IMAGE_NAME, --image_name IMAGE_NAME
                        Image Name
  -o IMAGE_OVERRIDE, --image_override IMAGE_OVERRIDE
                        Image Override Name
  -p PROJECT_NAME, --project_name PROJECT_NAME
                        Project Name
  -a BUILD_ARG, --build_arg BUILD_ARG
                        Build Arg
  -d DOCKERFILE, --dockerfile DOCKERFILE
                        Dokerfile Name
  -t [TAGS_LIST [TAGS_LIST ...]], --tags_list [TAGS_LIST [TAGS_LIST ...]]
                        Tags other than "latest"
```

[↑ Table des matières ↑](##sections)

## `Test.Dockerfile`

CodeBuild n'étant pas très flexible et la phase de test s'exécutant uniquement depuis l'image générer par Test.Dockerfile, quelques modifications ont dû être fait pour permettre l'exécution de Python et de commande AWS CLI.

```Dockerfile
RUN apt-get install git python3 awscli -yqq
```

[↑ Table des matières ↑](##sections)

## Build

CodeBuild est divisé en 4 phases.

### `install`

Phase d'installation de dépendances, je ne l'ai pas utilisé.

### `pre_build`

Phase de configuration, je l'utilise ici pour me connecter au registre Docker.

```yml
phases:
  pre_build:
    commands:
      - echo "Pre Build"
      - python3 ./scripts/codebuild_helper.py --registry_login --username $DOCKER_USERNAME --password $DOCKER_PASSWORD --registry $DOCKER_REGISTRY
    finally:
      - echo "Finally Pre Build"
  ...
```

J'appel donc ma fonction `registry_login` en lui passant les arguments nécessaire à son exécution: `username`, `password`, `registry`

```python
def registry_login(username, password, registry="docker.io"):
    res, err = console_command(["docker", "login", "-u", username, "--password-stdin", registry], stdin=password)
```

`registry_login` appel donc `console_command` qui exécutera la commande `docker login -u username --password-stdin registry`. Le mot de passe sera passé par `STDIN`.

### `build`

L'étape du build représente notre fonctionnalité principale.

```yml
phases:
  ...
  build:
    commands:
      - echo "Build"
      - python3 ./scripts/codebuild_helper.py --build_docker --image_name $DOCKER_USERNAME/$PHP_IMAGE --tags_list latest $CODEBUILD_RESOLVED_SOURCE_VERSION --dockerfile Dockerfile
      - python3 ./scripts/codebuild_helper.py --build_docker --image_name $DOCKER_USERNAME/$PHP_TEST_IMAGE --tags_list latest $CODEBUILD_RESOLVED_SOURCE_VERSION --dockerfile Test.Dockerfile --build_arg "base_image=$DOCKER_USERNAME/$PHP_IMAGE:latest"
    finally:
      - echo "Finally Build"
  ...
```

Qui utilisera la fonction `build_docker` avec les arguments représentant le nom de l'image, la liste de tags, le nom du Dockerfile et les arguments de *builds*.

```python
def build_docker(image_name, tags_list=[], dockerfile="Dockerfile", build_arg=""):
    tags_set = {"latest"}
    tags_set |= set(tags_list)
    tags = []
    # Établir les tags à passer en command.
    for tag in list(tags_set):
        tags.append("--tag")
        tags.append(f"{image_name}:{tag}")
    res, err = console_command(["docker", f"pull --quiet {image_name}:latest"])
    # Build d'un image avec argument
    if build_arg:
        res, err = console_command(["docker", "build", "--quiet", "--cache-from", f"{image_name}:latest", "--build-arg", build_arg, *tags, "--file", f"docker/{dockerfile}", "docker/"])
        if err:
            raise AssertionError(f"{err}")
    # Build d'un image sans argument
    else:
        res, err = console_command(["docker", "build", "--quiet", "--cache-from", f"{image_name}:latest", *tags, "--file", f"docker/{dockerfile}", "docker/"])
        if err:
            raise AssertionError(f"{err}")
    # Publication des images
    for tag in tags:
        if tag != "--tag":
            res, err = console_command(["docker", "push", tag])
            if err:
                raise AssertionError(f"{err}")
```

La présence d'un `err` dans le retour de `console_commande` représente un message d'erreur. Je lève donc un erreur avec qui sera attrapé dans le `main` pour ensuite être géré par la fonction `error_handler`.

```python
if __name__ == '__main__':
    args = parser.parse_args()
    ...
    elif args.build_docker:
        try:
            build_docker(image_name=args.image_name, tags_list=args.tags_list, dockerfile=args.dockerfile, build_arg=args.build_arg)
        except AssertionError as err:
            environ['FAIL'] = 'BUILD'
    ...
    error_handler(environ.get("FAIL", "NO_ERROR"))
```

```python
def error_handler(code):
    if code == "PRE_BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
        exit(42)
    elif code == "BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
        exit(42)
    elif code == "POST_BUILD":
        print(f"FAIL {code}, DO SOMETHING WITH THAT")
        exit(42)
    else:
        print('NO FAIL')
```

### `post_build`

J'utilise cette section pour déclencher l'étape suivante depuis la fonction `trigger_codebuild` en identifiant le nom du projet CodeBuild. J'ai aussi intégré la possibilité d'overrider l'image dans laquelle s'exécute CodeBuild permettant un peu de flexibilité, celà pourrait aussi permettre d'utiliser le même projet CodeBuild pour tester du code PHP sur des images ayant diver version.

```yml
phases:
  ...
  post_build:
    commands:
      - python3 ./scripts/codebuild_helper.py --trigger_codebuild --project_name $TEST_JOB_NAME --image_override $DOCKER_USERNAME/$PHP_TEST_IMAGE:latest
    finally:
      - echo "Finally Post Build"
```

```python
def trigger_codebuild(project_name, image_override=""):
    err = False
    if image_override:
        res, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name, "--image-override", image_override])
    else:
        res, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name])
    # print(_)
    if err:
        raise AssertionError(f"{err}")
```

À noter que cette étape ne sera pas exécuté si le `Build` échoue à cause de ce segment:

```python
if __name__ == '__main__':
    args = parser.parse_args()
    is_error = True if not int(environ.get('CODEBUILD_BUILD_SUCCEEDING', 1)) else False
    if is_error:
        exit()
    ...
```

On utilise la variable de CodeBuild `CODEBUILD_BUILD_SUCCEEDING` pour connaître l'état de notre *build*, `0` pour échec, `1` pour succès.

[↑ Table des matières ↑](##sections)

## Test

### `install`

Phase d'installation de dépendances, je ne l'ai pas utilisé.

### `pre_build`

Phase de configuration, cette phase n'a pas été nécessaire.

### `build`

L'étape du build représente notre fonctionnalité principale.

```yml
phases:
  ...
  build:
    commands:
      - echo "Build"
      - echo Unit Test
      - phpunit --bootstrap ./src/Calculator.php ./tests/CalculatorTest.php
      - phpunit --bootstrap ./src/Email.php ./tests/EmailTest.php
      - echo Integration Test
      - phpunit --bootstrap ./src/Music.php ./tests/MusicIntegrationTest.php
      - echo Functional Test
      - phpunit --bootstrap ./src/Music.php ./tests/MusicFunctionalTest.php
    finally:
      - echo "Finally Build"
  ...
```

Il s'agit simplement de l'exécution des différents tests. L'échec d'un test annulera l'exécution des subséquentes.

### `post_build`

J'utilise cette section pour déclencher l'étape suivante depuis la fonction `trigger_codebuild` en identifiant le nom du projet CodeBuild. J'ai aussi intégré la possibilité d'overrider l'image dans laquelle s'exécute CodeBuild permettant un peu de flexibilité, celà pourrait aussi permettre d'utiliser le même projet CodeBuild pour tester du code PHP sur des images ayant diver version.

```yml
phases:
  ...
  post_build:
    commands:
      - python3 ./scripts/codebuild_helper.py --trigger_codebuild --project_name $CHATOPS_JOB_NAME
    finally:
      - echo "Finally Post Build"
```

```python
def trigger_codebuild(project_name, image_override=""):
    err = False
    if image_override:
        res, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name, "--image-override", image_override])
    else:
        res, err = console_command(["aws", "codebuild", "start-build", "--project-name", project_name])
    # print(_)
    if err:
        raise AssertionError(f"{err}")
```

À noter que cette étape ne sera pas exécuté si le `Build` échoue à cause de ce segment:

```python
if __name__ == '__main__':
    args = parser.parse_args()
    is_error = True if not int(environ.get('CODEBUILD_BUILD_SUCCEEDING', 1)) else False
    if is_error:
        exit()
    ...
```

On utilise la variable de CodeBuild `CODEBUILD_BUILD_SUCCEEDING` pour connaître l'état de notre *build*, `0` pour échec, `1` pour succès.

[↑ Table des matières ↑](##sections)

## ChatOps

### `install`

Phase d'installation de dépendances, je ne l'ai pas utilisé.

### `pre_build`

Phase de configuration, cette phase n'a pas été nécessaire.

### `build`

L'étape du build représente notre fonctionnalité principale.

```yml
phases:
  ...
  build:
    commands:
      - echo "Build"
      - echo "To start the Deploy Job execute"
      - echo "aws codebuild start-build --project-name $DEPLOY_JOB_NAME"
    finally:
      - echo "Finally Build"
  ...
```

N'ayant aucun outils d'interaction avec Slack ou autre, j'affiche la commande à éxécuter via AWS CLI pour démarrer l'étape du déploiement. Cette commande pourrait être utilisé via une fonction Lambda.

### `post_build`

Cette phase n'a pas été nécessaire.

[↑ Table des matières ↑](##sections)

## Deploy

### `install`

Phase d'installation de dépendances, je ne l'ai pas utilisé.

### `pre_build`

Phase de configuration, cette phase n'a pas été nécessaire.

### `build`

Ici s'exécuterai les fonctionnalités de déploiement. Il pourrait probablement être possible de démarrer CodeDeploy via AWS CLI.

### `post_build`

Cette phase n'a pas été nécessaire.

[↑ Table des matières ↑](##sections)
