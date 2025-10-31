# README - security_ssh

## Purpose

The `security_ssh` task set is designed to harden SSH settings on Linux systems to improve security by enforcing best practices and reducing potential attack surfaces.

## Need

This is needed when:
- Setting up production or sensitive systems where SSH access must be tightly controlled.
- Enforcing organizational or compliance-level SSH policies (e.g., disabling root login, enforcing key-based authentication).
- Reducing risks from brute force attacks or misconfigured default settings.

## What it does

- Disables direct SSH access for the root user.
- Enforces protocol settings (e.g., Protocol 2 only).
- Optionally restricts SSH to certain users or groups.
- Updates `sshd_config` safely to apply changes without breaking access.

> These tasks help ensure consistent, secure SSH configurations across all nodes in your infrastructure.
