# Microproyecto 2 - Computación en la Nube

Despliegue de un clúster de Azure Kubernetes Service (AKS) con dos aplicaciones de machine learning y supervisión activa, como parte del curso de Computación en la Nube de la Especialización en Inteligencia Artificial (UAO).

## Qué incluye este repositorio

- `01-cluster-aks`: notas y comandos de creación/destrucción del clúster.
- `02-image-classifier`: clasificador de imágenes (PyTorch/torchvision, ResNet18 preentrenado en ImageNet). API en Flask.
- `03-app-propia`: clasificador de vinos con scikit-learn (dataset `load_wine`). API en Flask.
- `04-monitoreo`: evidencias de supervisión y monitoreo en AKS.
- `vm-docker`: Vagrantfile de una máquina virtual local usada como banco de pruebas antes de desplegar en Azure (opcional, no se necesita para replicar el despliegue en Azure).

## Arquitectura

Un grupo de recursos con tres piezas: un clúster AKS (mínimo 2 nodos), un Azure Container Registry (ACR) donde viven las imágenes de Docker, y un workspace de Log Analytics para las métricas y logs. Cada aplicación corre como un `Deployment` con un `Service` de tipo `LoadBalancer`, expuesta con IP pública propia.

## Requisitos previos

- Cuenta de Azure con una suscripción activa (este proyecto se probó sobre Azure for Students).
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) instalado y autenticado (`az login`).
- Docker Desktop, con soporte para `buildx` (necesario si vas a construir para una arquitectura distinta a la de tu máquina, por ejemplo ARM64).
- `kubectl`.
- Git.

## Guía de despliegue paso a paso

Reemplaza `<TU_GRUPO_DE_RECURSOS>`, `<TU_REGION>`, `<TU_CLUSTER>`, `<TU_ACR>` y `<TU_VM_SIZE>` por los valores que quieras usar.

### 1. Crear el grupo de recursos y el clúster AKS

```bash
az group create --name <TU_GRUPO_DE_RECURSOS> --location <TU_REGION>

az aks create --resource-group <TU_GRUPO_DE_RECURSOS> --name <TU_CLUSTER> \
  --node-count 2 --node-vm-size <TU_VM_SIZE> --generate-ssh-keys

az aks get-credentials --resource-group <TU_GRUPO_DE_RECURSOS> --name <TU_CLUSTER>
kubectl get nodes
```

> **Si usas Azure for Students:** la suscripción restringe tanto las regiones como los tamaños de VM disponibles, de forma independiente a la cuota. Si `az aks create` falla, revisa la lista de tamaños permitidos que trae el mismo mensaje de error, y cruza esa lista contra tu cuota real con `az vm list-usage --location <TU_REGION> -o table`. En este proyecto la combinación que funcionó fue `Standard_B2ps_v2` (ARM64) en `canadacentral`.

### 2. Crear el Container Registry y conectarlo al clúster

```bash
az acr create --resource-group <TU_GRUPO_DE_RECURSOS> --name <TU_ACR> --sku Basic --location <TU_REGION>
az aks update --resource-group <TU_GRUPO_DE_RECURSOS> --name <TU_CLUSTER> --attach-acr <TU_ACR>
```

### 3. Actualizar las imágenes en los manifiestos

Antes de desplegar, edita `02-image-classifier/deployment.yaml` y `03-app-propia/deployment.yaml`, y reemplaza `acrmicroproyecto2jea.azurecr.io` por `<TU_ACR>.azurecr.io`.

### 4. Construir y subir las imágenes

Si tus nodos son de arquitectura `amd64` (lo más común), puedes construir de forma normal:

```bash
cd 02-image-classifier
az acr login --name <TU_ACR>
docker build -t <TU_ACR>.azurecr.io/clasificador-imagenes:v1 .
docker push <TU_ACR>.azurecr.io/clasificador-imagenes:v1

cd ../03-app-propia
docker build -t <TU_ACR>.azurecr.io/app-vino:v1 .
docker push <TU_ACR>.azurecr.io/app-vino:v1
```

Si tus nodos son ARM64 (como en este proyecto) y estás construyendo desde una máquina x86_64, necesitas `buildx` con emulación:

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
docker buildx create --use
docker buildx build --platform linux/arm64 -t <TU_ACR>.azurecr.io/clasificador-imagenes:v1 --push .
```

(repite el mismo build para `03-app-propia` con la imagen `app-vino`).

### 5. Desplegar las aplicaciones

```bash
kubectl apply -f 02-image-classifier/deployment.yaml
kubectl apply -f 03-app-propia/deployment.yaml
kubectl get pods
kubectl get services
```

Espera a que los pods queden en `Running` y anota las IP externas (`EXTERNAL-IP`) de cada servicio.

### 6. Habilitar monitoreo

```bash
az monitor log-analytics workspace create --resource-group <TU_GRUPO_DE_RECURSOS> --workspace-name <TU_WORKSPACE> --location <TU_REGION>

$workspaceId = az monitor log-analytics workspace show --resource-group <TU_GRUPO_DE_RECURSOS> --workspace-name <TU_WORKSPACE> --query id -o tsv

az aks enable-addons -a monitoring --resource-group <TU_GRUPO_DE_RECURSOS> --name <TU_CLUSTER> --workspace-resource-id $workspaceId
```

En el Portal de Azure, dentro del clúster, revisa "Métricas" (CPU/memoria en tiempo real) y "Registros" (consultas KQL sobre logs y pods).

### 7. Autoescalado horizontal (opcional)

```bash
kubectl autoscale deployment clasificador-imagenes --cpu-percent=50 --min=1 --max=4
kubectl get hpa
```

## Probar las aplicaciones

```bash
curl -X POST -F "img=@imagen.jpg" http://<IP-EXTERNA-CLASIFICADOR>/predict
```

## Problemas comunes en Azure for Students

- **Región o tamaño de VM no permitido**: el mensaje de error de `az aks create` incluye la lista completa de tamaños permitidos; cruza esa lista con `az vm list-usage --location <TU_REGION> -o table` para encontrar uno con cuota disponible.
- **`ACR Tasks` bloqueado** (compilación en la nube): construye las imágenes localmente con `docker build`/`docker buildx` y súbelas con `docker push`, en vez de `az acr build`.
- **PowerShell**: el `curl` de PowerShell es un alias de `Invoke-WebRequest` y no acepta la sintaxis de curl real. Usa `curl.exe` explícitamente, o `Invoke-RestMethod` con `-Form` (PowerShell 7+).

## Limpiar recursos

Para no consumir créditos innecesarios mientras no lo estés usando:

```bash
az aks delete --resource-group <TU_GRUPO_DE_RECURSOS> --name <TU_CLUSTER> --yes --no-wait
```

El Container Registry y el workspace de monitoreo se conservan, así que no hace falta reconstruir las imágenes para volver a desplegar.

## Autores

- Juan Esteban Aristizábal - 22601265
- Juan Felipe Lopez - 22615417
- John Angel Posso - 22615413

