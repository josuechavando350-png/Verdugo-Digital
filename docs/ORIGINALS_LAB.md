# GrowthBook + Mautic original-application laboratory

Run only on a disposable authorized Linux Docker host:

```sh
VERDUGO_LAB_CONFIRM=synthetic-only bash scripts/originals-lab.sh
```

This starts real official images and databases on an internal Docker network.
The host discovers private IPs only from the exact network created for this run;
no public bind or outbound network is added. Credentials are generated locally,
never committed. The script initializes Mautic via its original CLI and GrowthBook
via its original APIs. No fake provider HTTP server or invented database fixture
stands in for an application.

Acceptance requires a real GrowthBook feature write/readback, a Mautic contact
whose tag comes from the returned feature value, contact readback, rejection of
missing authentication, and matching data after every app and database is stopped
and started with volumes retained. The bridge is glue, not a replacement provider.

Original packaging/API sources:
- https://github.com/mautic/docker-mautic
- https://github.com/growthbook/growthbook/tree/v5.2.0

Image digests are recorded in bounded evidence per run. A mutable registry tag
is not claimed to equal this repository's source gitlink. The workflow uploads
only image identities and sanitized acceptance checks. Configs, credentials and
raw logs stay in `.lab-private/`, excluded from Git. Only synthetic example.invalid
contacts are created; no production campaign, message, or paid host is activated.

Exit cleanup destroys this run's containers and volumes: a passing test is NOT a
permanent deployment. Android and all-ten acceptance remain false. The separate
Mautic/Countly native-pair laboratory is preserved; neither pair alone certifies
a simultaneous three-way or ten-way product. Consult the run for the exact commit,
not this document, to determine which tests actually passed.
