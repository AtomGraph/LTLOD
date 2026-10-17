> **Status: survey, 2026-10-17.** A snapshot of the domain registries. Availability changes, so re-check before registering.

# `linkeddata.<ccTLD>` availability across Europe

## Context
This is a survey of which country-code `linkeddata.*` domains are still free, in case other countries get the LTLOD setup.

## Method
I checked 33 TLDs: EU-27, `.eu`, the EEA countries (`.is`, `.no`, `.li`), `.ch` and `.uk`.
- DNS: `dig NS` and `dig A` for every domain.
- WHOIS for each domain with no NS record, because a registered domain can still be undelegated. Where the IANA referral returned no domain data, I queried the registry's WHOIS server directly.
- A domain counts as **free** only when the registry itself said so ("not found", "available", "free"). When DNS returned NXDOMAIN but the registry gave no answer, the domain is **probably free**.

## Free: confirmed by the registry (18)
| TLD | Registry answer |
|---|---|
| .at | nothing found |
| .be | Status: AVAILABLE |
| .bg | registration status: available |
| .hr | No entries found |
| .cz | no entries found |
| .ee | Domain not found |
| .fi | Domain not found |
| .fr | NOT FOUND |
| .ie | Not found |
| .lv | Status: free |
| .lu | No such domain |
| .pl | No information available |
| .ro | No entries found |
| .sk | Domain not found |
| .se | not found |
| .is | No entries found |
| .no | No match |
| .uk | This domain name has not been registered |

## Probably free: NXDOMAIN, but no registry answer (6)
Check these on the registry websites.

| TLD | Why it is unconfirmed |
|---|---|
| .hu | whois.nic.hu returned an empty reply. Check at https://www.domain.hu |
| .pt | whois.dns.pt timed out. Check at https://www.dns.pt |
| .cy | No public WHOIS. Check at https://www.nic.cy (most names are registered under `.com.cy`) |
| .gr | No public WHOIS. Check at https://grweb.ics.forth.gr |
| .mt | No public WHOIS. Check at https://www.nic.org.mt (most names are registered under `.com.mt`) |
| .li | WHOIS is blocked for scripted clients. Check at https://www.nic.ch/whois/ |

## Taken (9)
| Domain | Nameservers | What's there |
|---|---|---|
| linkeddata.lt | serveriai.lt | LTLOD |
| linkeddata.eu | serveriai.lt | Ours, no content yet |
| linkeddata.de | Hetzner | eccenca ("Enterprise Knowledge Graph Solutions") |
| linkeddata.es | servidoresdns.net | "Linked Data Applications", on an IP in a Madrid university's range (138.100.x) |
| linkeddata.nl | TransIP | Registered, no content |
| linkeddata.dk | DanDomain | Registered, no content |
| linkeddata.it | ParkLogic | Parked; may be for sale |
| linkeddata.si | Hostinger | Parked; may be for sale |
| linkeddata.ch | hostserv.eu | Registered, no content |

## Before registering
Some registries require local presence or limit who can register (for example .hr, .no, .is, and .pl for some uses). I haven't checked these rules. Look them up for each TLD you plan to register.
