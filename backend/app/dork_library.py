"""
Google Dork Library — categorized dorks for reconnaissance.
Each dork uses {target} as placeholder for the domain.
"""
from __future__ import annotations

DORK_CATEGORIES: dict[str, dict] = {
    "exposed_files": {
        "label": "Exposed Files",
        "icon": "📁",
        "description": "Find exposed sensitive files indexed by Google",
        "dorks": [
            'site:{target} filetype:pdf',
            'site:{target} filetype:xls OR filetype:xlsx',
            'site:{target} filetype:doc OR filetype:docx',
            'site:{target} filetype:sql',
            'site:{target} filetype:log',
            'site:{target} filetype:env',
            'site:{target} filetype:bak',
            'site:{target} filetype:conf OR filetype:config',
            'site:{target} filetype:xml',
            'site:{target} filetype:json',
        ],
    },
    "login_pages": {
        "label": "Login Pages",
        "icon": "🔐",
        "description": "Discover admin panels and login interfaces",
        "dorks": [
            'site:{target} inurl:admin',
            'site:{target} inurl:login',
            'site:{target} inurl:dashboard',
            'site:{target} inurl:portal',
            'site:{target} inurl:signin',
            'site:{target} inurl:administrator',
            'site:{target} inurl:wp-admin',
            'site:{target} inurl:cpanel',
            'site:{target} intitle:"admin panel"',
            'site:{target} intitle:"login" inurl:admin',
        ],
    },
    "vulnerabilities": {
        "label": "Vulnerability Indicators",
        "icon": "⚠️",
        "description": "Find potentially vulnerable endpoints",
        "dorks": [
            'site:{target} inurl:phpinfo.php',
            'site:{target} inurl:test.php',
            'site:{target} inurl:install.php',
            'site:{target} inurl:setup.php',
            'site:{target} inurl:.git',
            'site:{target} inurl:wp-config',
            'site:{target} intitle:"Index of /"',
            'site:{target} inurl:debug',
            'site:{target} inurl:console',
            'site:{target} intitle:"phpMyAdmin"',
        ],
    },
    "email_harvest": {
        "label": "Email Harvesting",
        "icon": "📧",
        "description": "Find email addresses associated with the target",
        "dorks": [
            'site:{target} "@{target}"',
            '"{target}" email contact',
            'site:{target} intext:"@{target}"',
            '"{target}" filetype:pdf email',
            'site:{target} "contact us" email',
        ],
    },
    "subdomains": {
        "label": "Subdomain Discovery",
        "icon": "🔍",
        "description": "Discover subdomains via Google indexing",
        "dorks": [
            'site:*.{target} -www',
            'site:*.{target}',
            'site:{target} -www',
            'inurl:{target} -site:{target}',
        ],
    },
    "sensitive_info": {
        "label": "Sensitive Information",
        "icon": "🔒",
        "description": "Find accidentally exposed sensitive data",
        "dorks": [
            'site:{target} "password" filetype:log',
            'site:{target} "api_key" OR "api key" OR "apikey"',
            'site:{target} "secret" filetype:env',
            'site:{target} intext:"DB_PASSWORD"',
            'site:{target} "private key"',
            'site:{target} intext:"Authorization: Bearer"',
        ],
    },
}


def get_dorks(category: str, target: str) -> list[str]:
    """Return list of dorks for a category with target substituted."""
    cat = DORK_CATEGORIES.get(category)
    if not cat:
        return []
    return [d.replace("{target}", target) for d in cat["dorks"]]


def list_categories() -> list[dict]:
    """Return all categories metadata."""
    return [
        {
            "key": k,
            "label": v["label"],
            "icon": v["icon"],
            "description": v["description"],
            "count": len(v["dorks"]),
        }
        for k, v in DORK_CATEGORIES.items()
    ]
