What is Procession?
===================

Procession is software that enables a controlled gate process for
software developers. There are two main functions of Procession:

* Manage Git repositories
* Enabled code review and approval in a controlled fashion

Procession has a number of components that enable the above
functionality:

* `processiond` -- Provides a RESTful API service for managing
  source repositories, doing code reviews, and configuring
  merge gates
* `procession-www` -- A Django web application that exposes
  code review and administrative functionality
* `procession-git` -- A daemon that runs git commands and communicates
  with `processiond`

Why Procession?
===============

Procession was borne out of frustration with the Gerrit open source
code review and repository management systems. Gerrit, perhaps the
most feature-ful of available systems, suffers from a number of
problems that Procession aims to solve:

* Installing and configuring Gerrit is tedious and error-prone, mostly
  due to the manual steps required for many actions and the fact
  that it is not packaged software
* It is written in Java and Prolog, making contributions from developers
  in more popular modern platforms like Python, Ruby or PHP, virtually
  impossible
* The user interface is neither complete (some things must be done directly
  against the database, for example) and not very intuitive
* The database schema used by Gerrit is duplicative and the code that
  interfaces with the database is obtuse and hard to understand

Note that we're not saying Gerrit is a bad system. Just that it has
some weaknesses that are troublesome, and we think should be addressed...
so we addressed them by creating Procession.
