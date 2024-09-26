# OAI RAN CU (Central Unit) Operator (k8s)
[![CharmHub Badge](https://charmhub.io/oai-ran-cu-k8s/badge.svg)](https://charmhub.io/oai-ran-cu-k8s)

A Charmed Operator for the OAI RAN Central Unit (CU) for K8s.

## Pre-requisites

A Kubernetes cluster with the Multus addon enabled.

## Usage

Enable the Multus addon on MicroK8s.

```bash
sudo microk8s addons repo add community https://github.com/canonical/microk8s-community-addons --reference feat/strict-fix-multus
sudo microk8s enable multus
```

Deploy the charm.

```bash
juju deploy oai-ran-cu-k8s --trust --channel=2.1/edge
juju deploy sdcore-amf-k8s --trust --channel=1.5/edge
juju integrate oai-ran-cu-k8s:fiveg_n2 sdcore-amf-k8s:fiveg-n2
```

## Image

- **oai-ran-cu**: `ghcr.io/canonical/oai-ran-cu:2.1.1`
