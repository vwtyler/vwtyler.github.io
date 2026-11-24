---
title: "Building and Maintaining a Production Application with ChatGPT and GitHub"
date: 2026-11-24 12:15:00 -0800
description: "What developing Radiant with ChatGPT's GitHub integration actually looks like, and why human oversight still matters."
categories: [radiant]
tags: [chatgpt, ai, github, github-actions, development, automation]
---

I've been using ChatGPT to build [Radiant](https://github.com/vwtyler/radiant), a self-hosted radio operations platform for community radio. It manages programming schedules, now-playing information, playlist history, and reporting, with an admin interface and WordPress components for displaying station information.

Radiant grew out of a larger effort to modernize things at KAAD-LP. Earlier this year I wrote about [replacing a desktop-based streaming setup with Liquidsoap](/posts/winamp-shoutcast-dsp-to-liquidsoap/) and [automating song metadata for Icecast](/posts/icecast-metadata-systemd-service/). Radiant addresses a different set of problems, but the goal is similar: reduce the amount of manual work involved in keeping a volunteer-run radio station operating.

What's different about working on Radiant is how much of the implementation I've delegated to ChatGPT, and how directly it can interact with the project.

This isn't an introduction to generating code with AI. It's more about what happens when that code lives in a real repository, gets deployed to a real server, and needs to continue working after the next change.

## From copying code to working in the repository

There is a big difference between asking ChatGPT to write a function and asking it to make a change to an application it can actually inspect.

With the GitHub integration connected, I can ask ChatGPT to look at how a feature currently works before proposing a change. It can read the relevant files, make changes on a branch, commit them, and open a pull request. I don't have to manually copy the contents of each file from the chat window into an editor.

That also means the discussion can be about the application rather than the mechanics of moving code around.

A typical exchange starts with something like a screenshot of an error or a description of a feature I want. For example, I recently wanted to clean up the user management screen in Radiant. Instead of starting with React components or API endpoints, I described what the interface should do: consolidate the list, indicate pending invitations next to the email address, and provide controls to resend or delete invitations and reset passwords.

The implementation details are still important, but they don't have to be the starting point of the conversation.

## What the workflow looks like

The process I've been using generally looks like this:

1. Describe the problem or the behavior I want.
2. Have ChatGPT inspect the relevant parts of the repository and propose a change.
3. Have it implement the agreed change on a separate branch and open a pull request.
4. Review the changes and check what validation has actually been performed.
5. Approve the merge when I'm satisfied, check GitHub Actions, and test the deployed application.

GitHub is useful here because the conversation isn't the only record of what happened. There are commits, diffs, pull requests, and workflow runs. I can go back and see what changed even if the chat has moved on to something else.

I don't treat a pull request being opened as evidence that the feature works, or a successful workflow as evidence that the feature behaves correctly for a user. Those are different checks. A successful build can still produce an application with a broken interface or incorrect scheduling logic.

## An example: separating deployment from development

I recently went through the process of [splitting Radiant's application code and production deployment into two repositories](/posts/radiant-separating-code-and-deployment/).

The original setup worked, but the public repository was accumulating workflows specific to my VPS. I wanted someone else to be able to clone Radiant without also inheriting the machinery I use to administer my server.

ChatGPT helped implement a separate private deployment repository. An intermediate version used scheduled GitHub Actions to poll the public repository for updates.

As we were going through the setup, I found myself asking where I could see the scheduled workflow and how it was configured. That led to a more fundamental question: why are we polling the project repository when GitHub already knows when a push happens?

We changed the architecture again. Now a push to the public main branch sends an event to the private repository, which handles the production update. The polling workflow is no longer necessary.

This is a good example of both the usefulness and the limitations of the process. ChatGPT was able to implement the automation, but it also implemented an approach that added unnecessary complexity for this particular problem. The fact that something can be built doesn't mean it should be built that way.

## Knowing what needs to stay the same

Another example is Radiant's scheduling logic. At a community radio station, not every program airs every week. Some programs alternate between the first and third weekends of the month, while others air on the second and fourth.

When asking ChatGPT to review that logic, my concern wasn't simply whether it could come up with a cleaner implementation. It was whether the change would affect the schedule we already had.

That's an important distinction. A refactor can look perfectly reasonable in isolation and still cause problems if it changes the behavior of an existing system. With scheduling, I'd want representative cases from the current schedule, including months with five weekends, to be part of the validation before relying on a change.

The station's actual requirements and operating practices aren't necessarily apparent from the source code. That context is something I have to bring to the conversation.

## Directing development is still work

One thing I've noticed is how easy it is to keep moving from one change to the next. Ask for a feature, get a pull request, merge it, find something else to improve. The time between having an idea and seeing it implemented can be surprisingly short.

That doesn't eliminate the need to decide what belongs in the application. If anything, it makes that part more important. Adding a feature is easier, but maintaining it is still a responsibility.

Some questions I try to keep in mind:

- Does this solve the actual problem, or just the one I initially described?
- Is there a simpler approach?
- What existing behavior might this change?
- What happens if the new workflow fails halfway through?
- How will I know whether the change is actually running in production?

I also ask ChatGPT to validate changes, but I need to distinguish between reviewing code, running automated checks, and testing the actual deployed application. The GitHub integration isn't the same thing as unrestricted access to the server, and an answer in chat isn't a substitute for evidence from the system.

## Access, secrets, and production

Connecting an AI assistant to GitHub is different from pasting a snippet of code into a chat. Depending on the permissions granted, the assistant can change repository contents, modify automation, or merge a pull request.

In Radiant's case, merging into main can initiate a production deployment. That makes a merge more consequential than simply updating a file in a repository.

I keep production SSH credentials in the private deployment repository's Actions secrets and runtime configuration on the VPS. The public project uses a separate credential to notify the deployment repository. It's similar in principle to the separation of configuration and code I used for [my Cloudflare dynamic DNS setup](/posts/cloudflare-ddns-systemd-timer/), although the execution environment is different.

There are a few practices I would recommend to anyone trying this kind of workflow:

- Grant access only to the repositories and permissions actually needed.
- Keep credentials out of source files, pull requests, and chat messages.
- Use branches and pull requests rather than treating main as a scratchpad.
- Keep deployment permissions separate where practical, and protect the branches and workflows that can initiate a deployment.
- Require meaningful validation before merging, and have a way to recover when deployment goes wrong.

Separating the deployment repository helps, but it doesn't remove the trust relationship. Anyone who can change the public main branch can potentially change the code that runs on the server. The AI assistant's access needs to be understood in that context.

## Is it still my project?

I think a useful distinction is between writing the code and making the decisions about what the code should do. ChatGPT has done a substantial amount of the implementation work on Radiant. I'm defining what I want the application to do, supplying the station context, deciding which changes to accept, and dealing with the consequences of those decisions.

That isn't the same as claiming I wrote every line of code myself. It also isn't the same as an application being built autonomously without my involvement.

This post and the companion article about Radiant's deployment were themselves drafted with ChatGPT using the GitHub integration. The same process applies: inspect the existing work, draft a change, open a pull request, and leave the decision to publish to me.

For Radiant, the interesting thing isn't that an AI assistant can produce code. It's that I can use it as part of an ongoing development process, with a real application and an existing Git history. The measure of whether that process works is whether the resulting software is useful, reliable, and something I can continue to maintain.
