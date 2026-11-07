"""IT on-call pack: Kaveri Cloud — a payments platform with Bengaluru and Hyderabad regions."""
from .common import processed, rec, tip

CAT_KEY = {"Config Errors": "config", "Hardware/Power Failures": "hardware", "Conflicts": "conflicts", "Time": "time",
           "Database": "database", "Uncategorized": "general"}


def build():
    assets = [
        {"id": "PAY-API", "name": "payments-api (Bengaluru)", "model": "k8s service", "type": "Service", "type_key": "general", "site": "blr", "cost_per_hour": 50000},
        {"id": "PG-1", "name": "Postgres primary (Bengaluru)", "model": "Postgres 15 cluster", "type": "Database", "type_key": "database", "site": "blr", "cost_per_hour": 80000},
        {"id": "PG-2", "name": "Postgres primary (Hyderabad)", "model": "Postgres 15 cluster", "type": "Database", "type_key": "database", "site": "hyd", "cost_per_hour": 80000},
        {"id": "K8S-1", "name": "Kubernetes prod cluster (Bengaluru)", "model": "k8s 1.30 cluster", "type": "Cluster", "type_key": "config", "site": "blr", "cost_per_hour": 60000},
        {"id": "K8S-2", "name": "Kubernetes prod cluster (Hyderabad)", "model": "k8s 1.30 cluster", "type": "Cluster", "type_key": "config", "site": "hyd", "cost_per_hour": 60000},
        {"id": "DNS-1", "name": "Internal DNS", "model": "CoreDNS", "type": "DNS", "type_key": "config", "site": "blr", "cost_per_hour": 70000},
        {"id": "CERT-1", "name": "TLS certificates (public endpoints)", "model": "TLS certs", "type": "Certificates", "type_key": "time", "site": "blr", "cost_per_hour": 90000},
    ]
    people = [
        {"id": "srinivas", "name": "Srinivas Iyer", "short": "Srini", "role": "Principal SRE", "site": "blr", "experience_years": 16,
         "retiring_on": "2027-01-10", "speciality": "Databases, networking — moving abroad in January"},
        {"id": "neha", "name": "Neha Gupta", "short": "Neha", "role": "SRE Lead (Hyderabad)", "site": "hyd", "experience_years": 9,
         "retiring_on": None, "speciality": "Kubernetes, incident command"},
        {"id": "rahul", "name": "Rahul Verma", "short": "Rahul", "role": "On-call Engineer (joined Aug 2026)", "site": "blr", "experience_years": 0.3,
         "retiring_on": None, "speciality": "Learning — first on-call rotation"},
    ]
    R = [
        rec("i-001", "2026-05-06T02:10", "CERT-1", "srinivas", "TLS certificate expired", "Mobile app failing with SSL errors at 2 am",
            "Auto-renew job failing silently for 2 months", "Renewed certificate manually; fixed the renew job's DNS permission; added an alert at 30 and 7 days before expiry", mins=55),
        rec("i-002", "2026-05-20T14:30", "PG-1", "srinivas", "Database disk full", "Writes failing, disk at 100%",
            "WAL files piling up because the archive command was failing", "Fixed the archive_command credentials; let archiving catch up; added disk alert at 75%", mins=80),
        rec("i-003", "2026-06-09T19:05", "PAY-API", "neha", "5xx errors after deploy", "Error rate 12% right after the 19:00 deploy",
            "Bad config flag in the new release", "Rolled back first, debugged later; added canary deploy at 5% traffic", mins=18),
        rec("i-004", "2026-06-25T11:40", "PG-1", "rahul", "Too many connections", "API timeouts; Postgres says 'too many clients'",
            "Assumed slow queries", "Restarted API pods", outcome="failed_again", mins=40),
        rec("i-005", "2026-06-25T12:30", "PG-1", "srinivas", "Too many connections", "Same 'too many clients' after restart",
            "Connection pool per pod too large after scaling to 40 pods", "Put PgBouncer in transaction mode in front of Postgres; cut pool per pod from 20 to 5", mins=35),
        rec("i-006", "2026-07-14T03:20", "DNS-1", "srinivas", "Internal DNS failures", "Services can't resolve each other after a config push",
            "Typo in the forward zone pushed to all regions at once", "Rolled back the DNS config; added config lint and a one-region-first rollout", mins=42),
        rec("i-007", "2026-08-02T16:50", "K8S-1", "neha", "Nodes NotReady", "Several nodes NotReady, pods evicted",
            "Node disks full of old container images", "Cordoned and cleaned nodes; tuned image garbage-collection thresholds", mins=65),
        rec("i-008", "2026-08-19T00:15", "PG-1", "srinivas", "Clock skew alarms", "Payment signatures failing, clocks 40 s apart",
            "NTP service stopped on two DB hosts after an OS patch", "Restarted and enabled chrony; added clock-offset alert at 1 s", mins=30),
        rec("i-009", "2026-09-08T14:10", "PG-2", "rahul", "Too many connections", "Hyderabad DB 'too many clients' after scaling",
            "Pool per pod too large", "Followed Srini's fix from Ustaad (Bengaluru): PgBouncer transaction mode; pool per pod 5", mins=20),
        rec("i-010", "2026-09-29T02:40", "K8S-2", "rahul", "Nodes NotReady", "Hyderabad nodes NotReady at night",
            "Disk pressure from old images", "Followed Neha's fix from Ustaad: cordon, clean images, tune GC thresholds", mins=35),
        rec("i-011", "2026-10-15T19:20", "PAY-API", "rahul", "5xx errors after deploy", "Errors right after deploy", "Bad release",
            "Rolled back first (from Ustaad playbook), then debugged", mins=9),
        rec("i-012", "2026-10-30T01:55", "CERT-1", "rahul", "TLS certificate expiring", "Alert: certificate expires in 7 days", "Renew job hit rate limit",
            "Renewed with backoff; staggered renewals", mins=15, status="pending"),
    ]
    T = [
        tip("ti-01", "srinivas", "PG-1", "2026-05-21",
            "Before running any delete on a database server, type `hostname` and read it out loud to your pair. GitLab lost about 6 hours of production data in 2017 by deleting on the wrong server.",
            "GitLab 2017 public post-mortem"),
        tip("ti-02", "neha", "PAY-API", "2026-06-10", "Roll back first, debug later. If errors start right after a deploy, revert within 5 minutes — investigate on staging."),
        tip("ti-03", "srinivas", "DNS-1", "2026-07-15",
            "Never push DNS or edge config to all regions at once. One region first, watch for 10 minutes, then the rest — many big public outages were a single bad config pushed everywhere.",
            "Public post-mortems (Cloudflare, AWS config errors)"),
        tip("ti-04", "srinivas", "PG-1", "2026-06-26",
            "'Too many clients' after scaling pods is usually pool maths: pods × pool size > max_connections. Put PgBouncer in front before raising max_connections."),
        tip("ti-05", "srinivas", "CERT-1", "2026-05-07", "Alert on certificate expiry at 30 and 7 days, and alert when the renew job itself fails — silent renew failures cause 2 am outages."),
    ]
    pm = processed("it_postmortems.json") or {"items": [], "by_category": {}}
    logs = processed("it_logs.json") or {"systems": []}
    public = [{"id": x["id"], "title": f"{x['company']} outage ({x['category']})", "text": x["summary"], "fix": "",
               "source": "Public post-mortem", "date": "2020-01-01", "type_key": CAT_KEY.get(x["category"], "general"),
               "outcome": "open", "url": x["url"]} for x in pm["items"]]
    return {
        "id": "it", "name": "IT on-call", "icon": "💻", "color": "#7C3AED",
        "tagline": "What the principal SRE knows at 2 am",
        "org": {"name": "Kaveri Cloud (demo)", "note": "Demo payments platform with Bengaluru and Hyderabad regions. People are fictional; outage write-ups and logs are real.",
                "ustaad_started": "2026-09-01"},
        "labels": {"asset": "Service", "assets": "Services", "person": "Engineer", "record": "Incident", "problem": "Incident",
                   "code": "Error", "downtime": "Outage"},
        "cost_per_hour": 50000,
        "sites": [{"id": "blr", "name": "Bengaluru region"}, {"id": "hyd", "name": "Hyderabad region"}],
        "roles": [
            {"id": "oncall", "name": "On-call engineer", "can_approve": False, "tools": ["ask", "log", "memory", "playbook", "quiz", "passport", "outages"]},
            {"id": "lead", "name": "SRE lead", "can_approve": True, "tools": ["ask", "log", "memory", "approvals", "playbook", "risk", "interview", "shift", "skills", "passport", "stats", "outages", "quiz"]},
            {"id": "em", "name": "Engineering manager", "can_approve": True, "tools": ["stats", "risk", "shift", "skills", "passport", "ask", "memory", "approvals", "playbook", "interview", "outages", "quiz"]},
        ],
        "tools": ["outages"],
        "safety_line": "Mitigate first (roll back / fail over), then debug. Announce in the incident channel before risky commands.",
        "generic": {"default": ["Check recent deploys and config changes", "Check dashboards and error logs", "Roll back if a change just went out", "Escalate to the service owner"]},
        "questions": ["Postgres says too many clients after we scaled the API", "Errors started right after the 7 pm deploy",
                      "Which service had the most outage time?", "Internal DNS can't resolve after a config change"],
        "interview_extra": [
            {"topic": "Hidden dependencies", "question": "Which systems depend on each other in ways that are not in any diagram?", "why": "Hidden coupling causes the worst outages."},
            {"topic": "Dangerous commands", "question": "Which commands or buttons have you learned never to run in production, and why?", "why": "These lessons usually cost an outage to learn."}],
        "assets": assets, "people": people, "records": R, "tips": T, "public": public,
        "panels": [
            {"id": "pm-cats", "title": f"Causes of {len(pm['items'])} real public outages", "type": "bar",
             "data": {"labels": list(pm["by_category"].keys()), "values": list(pm["by_category"].values())}, "source": pm.get("source")},
            {"id": "logs", "title": "Most common log patterns in real systems (Loghub)", "type": "logs",
             "data": [{"system": s["system"], "top": s["top_patterns"][:3]} for s in logs["systems"] if s["system"] in
                      ("Linux", "OpenSSH", "Apache", "HDFS", "Zookeeper", "OpenStack", "Spark", "Hadoop")], "source": logs.get("source")},
        ],
    }
