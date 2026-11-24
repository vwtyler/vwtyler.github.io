---
title: "Building and Maintaining a Production Application with ChatGPT and GitHub"
date: 2026-11-24 12:15:00 -0800
description: "What developing Radiant with ChatGPT's GitHub integration actually looks like, and why human oversight still matters."
categories: [radiant]
tags: [chatgpt, ai, github, github-actions, development, automation]
---

I've been working on [Radiant](https://github.com/vwtyler/radiant), a self-hosted radio operations platform for community radio. It grew out of my work modernizing KAAD-LP's infrastructure, including [moving our stream to Liquidsoap](/posts/winamp-shoutcast-dsp-to-liquidsoap/) and [automating Icecast metadata](/posts/icecast-metadata-systemd-service/).

What's different about Radiant is how much of the development I've done through ChatGPT's GitHub integration.

## Beyond copying and pasting code

Rather than asking ChatGPT to generate code and then copying it into an editor, I can have it inspect the repository, modify files, create branches, and open pull requests directly.

My workflow generally looks like this:

1. Describe a problem or feature.
2. Have ChatGPT inspect the existing code and propose a solution.
3. Have it implement the change and open a pull request.
4. Review the changes and validation before approving the merge.
5. Check the deployment and test the application.

Sometimes the conversation starts with nothing more than a screenshot of something that isn't working or a description of how I'd prefer an interface to behave.

For example, I recently wanted to clean up Radiant's user management screen. I wanted one list of users and invitations, with pending invitations indicated next to the email address, and controls for resending invitations, deleting them, and resetting passwords. I could describe what I wanted the screen to look like without first figuring out which React components and API endpoints needed to change.

That doesn't mean the implementation details are irrelevant. It means I can start with the problem rather than the files. GitHub provides a record of what actually changed, independent of the conversation. If something breaks later, there is a commit history and a pull request to go back to.

There is also less friction when a change involves multiple files. Instead of keeping track of several code snippets and remembering where each one goes, I can review a single set of changes in the repository.

## Knowing when to push back

A good example is my recent effort to [separate Radiant's application code from its production deployment](/posts/radiant-separating-code-and-deployment/).

An intermediate solution implemented by ChatGPT had a private repository periodically polling the public repository for changes. As I was trying to understand how the scheduled workflows operated, I realized we were making things unnecessarily complicated. GitHub already knows when a push happens, so why not use that event directly?

We switched to an event-driven deployment. ChatGPT implemented both approaches, but it was important that I questioned the first one rather than just accepting it because it worked.

The difference between the two solutions wasn't really a question of whether ChatGPT could write the necessary YAML or shell commands. It was whether we had chosen the right architecture. A working implementation can still be the wrong answer to a problem, particularly when it introduces another service, workflow, or configuration that I'll need to maintain later.

The same applies to application features. When reviewing Radiant's scheduling logic for shows that air on alternating weekends, my main concern was preserving the existing schedule. A cleaner implementation isn't necessarily an improvement if it changes when a show is supposed to air.

For example, a month with five Saturdays is a useful test case. A show that airs on the first and third Saturday of every month isn't necessarily the same as a show that airs every other Saturday. The distinction matters to the people who make the schedule, even if the two patterns look similar in code.

Knowing what needs to stay the same is at least as important as knowing what I want to change. That's something I have to communicate explicitly when asking ChatGPT to modify an existing application.

## Working with a production application

Giving ChatGPT access to GitHub is more consequential than asking it to write a script. Merging a change to Radiant's main branch can trigger a production deployment.

I still need to understand what is being changed, protect credentials, and verify that the application actually works. A successful GitHub Actions run doesn't necessarily mean a feature behaves as intended. Keeping secrets separate from code, as I did in [my Cloudflare DDNS setup](/posts/cloudflare-ddns-systemd-timer/), is just as important here.

There are a few different things I want to know when a change is ready:

- Does the code do what I asked it to do?
- Have the relevant automated checks actually run?
- Did the deployment complete, and is the updated application running?
- Does the feature behave correctly when I use it?

Those are separate questions. Asking ChatGPT to validate a change is useful, but I still need to know what it was able to validate and what requires me to test it myself. Reading the code is not the same as running it, and a healthy API endpoint is not proof that the scheduling logic is correct.

Access is another consideration. Separating the deployment repository from the application repository lets me keep the production SSH credentials away from the public project's workflows. But the public repository can still initiate a deployment, so the separation doesn't eliminate the need to control what gets merged into main.

The integration removes a lot of the mechanical work of implementing changes, but it doesn't remove the responsibility of maintaining the application.

## Is it still my project?

I haven't personally written every line of Radiant's code. I have, however, been defining what the application should do, supplying the station context, questioning architectural decisions, and deciding which changes to accept.

There is a temptation, particularly when the time between describing a feature and seeing it implemented is so short, to keep adding things. I've found that it's worth spending some of that saved time thinking about whether I actually need the next feature, or whether the existing implementation could be simpler. Every new feature is another thing the project needs to support.

Even this post was drafted with ChatGPT through its GitHub integration, using the same branch and pull request process as the application.

For me, the interesting part isn't that ChatGPT can write code. It's that I can use it to maintain and develop an actual application over time. Whether that approach works ultimately depends on the quality and reliability of the software, not how quickly I can produce another pull request.
