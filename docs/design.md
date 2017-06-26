# Design

## Principles

These are the design principles that Procession is built with.

* Keep it simple, stupid

 * Installation of a simple environment should be painless

 * Getting started should be simple and  well-documented with examples

 * Integration with common, comfortable platforms for auth and
   code hosting should be seamless

 * If it smells too complex, it probably is

* Principle of least surprise

 * An action should have as few side-effects as possible and no side-effects
   that are not transparent to the user

* Services should do one thing and do it well

 * The UNIX philosophy is in full effect

* Choose boring technology

 * When possible use tried and true technology that Just Works over the next
   greatest fad technology

## Project Scope

The following use cases and items are in-scope for Procession:

* Fine-grained, but simple to understand, group and permission management
* Clear and easy management of code repository review and merge workflows
* Patch review system that promotes discussion and engagement with the code
  authors and reviewers
* Seamless and thoughtful integration with CI, testing, and code-hosting
  systems

These items are specifically **not** in-scope, and we are not interested in
adding functionality that reimplements these ideas:

* Source control systems. `git` is great. There's no reason to reimplement
  things that it does
* Code hosting facilities. Procession should work with existing code-hosting
  platforms like Github.com or gitorious or gitweb
