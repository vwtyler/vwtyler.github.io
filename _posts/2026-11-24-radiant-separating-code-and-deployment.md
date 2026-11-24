---
title: "Radiant: Separating Project Code from Production Deployment"
date: 2026-11-24 12:00:00 -0800
categories: [radiant]
tags: [radio, github-actions, docker, deployment, automation, self-hosting]
---

I've been working on [Radiant](https://github.com/vwtyler/radiant), a self-hosted radio operations platform for community radio stations like KAAD-LP. The name comes from **radi**o operations **a**ge**nt**.

There are a lot of little things that go into running a radio station that don't necessarily have much to do with getting audio out over the air. There's the programming schedule, keeping track of what played, putting that information on the station's website, and generating reports. Radiant is an attempt to bring some of those things together.

The project has a Node.js API, a React admin interface, PostgreSQL and Directus, and a WordPress plugin for displaying information on the public-facing website. The services run using Docker Compose.

As I've been working on it, I've also been trying to make it something that someone at another station could pick up and run themselves. That brought up a question about how I was deploying it: why should someone cloning Radiant get a bunch of GitHub Actions workflows specific to my server?

## The original setup

Originally I kept the application and the production deployment workflows in the same repository. A change to the main branch could kick off a GitHub Actions workflow that connected to my VPS over SSH and updated the running application.

That was convenient. I could work on the code, merge a pull request, and have the server updated without logging in separately. But as I added workflows for inspecting the server and recovering from deployment problems, the repository started accumulating things that were more about my particular installation than about Radiant itself.

There isn't anything inherently wrong with deploying from the same repository as your application. GitHub Actions secrets aren't included when someone clones a repository, for example. But the workflow files are, and those files don't necessarily make sense for someone running the application on their own hardware.

I wanted to retain automatic deployment without making my deployment setup part of the project someone else would inherit.

## Two repositories

I split things into two repositories with different responsibilities.

| Repository | Responsibility |
| --- | --- |
| [`radiant`](https://github.com/vwtyler/radiant) (public) | Application source, Docker Compose configuration, database migrations, documentation, and general CI |
| `radiant-deploy` (private) | Automation and credentials for updating my production VPS |

The public repository still contains everything needed to run Radiant. Someone can clone it, configure their environment, and use Docker Compose without needing access to my private repository.

The private repository doesn't contain a second copy of the application. It contains the automation for updating an existing checkout of the public repository on my VPS. That means there is still only one source of truth for the application code.

## Polling vs. events

One of the intermediate approaches was to have the private repository periodically check the public repository for changes. That would keep the public project largely unaware of the deployment process, but it also meant running a scheduled workflow even when there was nothing new to deploy.

It seemed unnecessary to have one repository continually ask another whether something had changed when GitHub already knows when a push happens.

The current setup uses GitHub's [repository dispatch event](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event). A small workflow in the public repository listens for pushes to `main` and sends an event to the private repository. The private repository then handles the actual deployment.

```text
Public repository (radiant)
    |
    | push to main
    v
GitHub Actions notification
    |
    | repository_dispatch
    v
Private repository (radiant-deploy)
    |
    | SSH
    v
Production VPS
    |
    +-- Fetch and fast-forward application code
    +-- Build API and admin images
    +-- Recreate application containers
    +-- Check health endpoints
```

There is no scheduled polling in the current setup. A merge to the public main branch is enough to initiate the process.

## How the repositories communicate

The notification workflow uses a fine-grained GitHub token stored as an Actions secret in the public repository. The token is scoped to the private deployment repository, with the Contents read/write permission needed by the dispatch API.

The request sends a custom event name and the commit SHA that triggered it. The receiving workflow listens for that event:

```yaml
on:
  repository_dispatch:
    types: [radiant-main-updated]
  workflow_dispatch:
```

The second trigger allows a deployment to be initiated manually as well. In the actual workflow I have a dry-run input that defaults to true, so I can inspect the server without updating the application.

The public [notification workflow](https://github.com/vwtyler/radiant/blob/main/.github/workflows/notify-private-deploy.yml) is small, but it is still specific to my installation. It is the one remaining connection between the project and my deployment. Someone adopting Radiant can remove or replace it rather than carrying over all of my production workflows. Without the dispatch secret, it currently fails if triggered by a push to main in their copy; it isn't needed to run Radiant.

## What happens on the VPS

The private workflow connects over SSH and fetches the latest public `main` branch. It then fast-forwards the local checkout rather than force-resetting it. If local changes prevent that update, the deployment stops rather than discarding those changes.

The application images are built while the old containers are still running. Once the build succeeds, the API and admin containers are recreated individually. PostgreSQL and Directus are left running.

The relevant Docker Compose commands are:

```bash
docker compose build radiant-api radiant-admin
docker compose up -d --no-deps radiant-api
docker compose up -d --no-deps radiant-admin
```

The workflow then checks that both application endpoints are responding. Only after those checks pass does it record the successfully deployed Git commit on the VPS.

That last part matters because a repeated notification doesn't necessarily mean there is anything new to deploy. If the latest commit has already been successfully deployed, the event-triggered workflow can skip the rebuild. If a deployment fails, a manual run can retry it.

The event includes the triggering commit for traceability, but the server actually deploys the latest available main branch when the workflow runs. This is a deployment of the current branch, not a release system that pins every event to an immutable artifact.

## A few things to keep in mind

Moving the workflows to a private repository does not make the system secure by itself. The production SSH credentials belong in the private repository's Actions secrets, and runtime configuration stays on the VPS. Any obsolete copies of deployment secrets in the public repository should be removed, and exposed credentials should be rotated.

The dispatch token is also a credential worth protecting. Although it doesn't contain the SSH key, it can trigger a workflow that has access to the production server. Access to modify workflows and merge into the public main branch should be treated accordingly.

Deleting workflow files from the public repository doesn't remove them from Git history, either. That is another reason not to put actual credentials into a workflow file in the first place.

This is also not a zero-downtime deployment. Recreating the application containers can cause a brief interruption, and I haven't implemented automatic rollback. The health checks tell me whether the new application responds, but they don't restore the old version if something goes wrong.

## Where this leaves Radiant

The first event-driven deployment succeeded on November 24, 2026. The old VPS-specific workflows were subsequently removed from the public project in [PR #11](https://github.com/vwtyler/radiant/pull/11), while general application CI remains there.

For my purposes, the important part is that I can still merge a change to Radiant and have it deployed automatically, but most of the machinery for managing my own server is no longer part of the application repository.

Someone who wants to run Radiant at another station shouldn't need to understand how I manage my VPS. They should just need to understand how to run Radiant.
