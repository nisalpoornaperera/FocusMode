import os

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
MARKER = "# FocusMode"

SOCIAL_MEDIA_DOMAINS = [
    "www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be",
    "www.facebook.com", "facebook.com", "m.facebook.com", "fb.com",
    "www.instagram.com", "instagram.com",
    "www.twitter.com", "twitter.com",
    "www.tiktok.com", "tiktok.com",
    "www.reddit.com", "reddit.com", "old.reddit.com",
    "www.snapchat.com", "snapchat.com",
    "www.pinterest.com", "pinterest.com",
    "www.tumblr.com", "tumblr.com",
    "www.twitch.tv", "twitch.tv",
]

ADULT_DOMAINS = [
    "pornhub.com", "www.pornhub.com",
    "xvideos.com", "www.xvideos.com",
    "xnxx.com", "www.xnxx.com",
    "xhamster.com", "www.xhamster.com",
    "redtube.com", "www.redtube.com",
    "youporn.com", "www.youporn.com",
    "tube8.com", "www.tube8.com",
    "spankbang.com", "www.spankbang.com",
    "brazzers.com", "www.brazzers.com",
    "onlyfans.com", "www.onlyfans.com",
    "chaturbate.com", "www.chaturbate.com",
    "stripchat.com", "www.stripchat.com",
    "livejasmin.com", "www.livejasmin.com",
    "cam4.com", "www.cam4.com",
    "bongacams.com", "www.bongacams.com",
    "camsoda.com", "www.camsoda.com",
    "myfreecams.com", "www.myfreecams.com",
    "fapello.com", "www.fapello.com",
    "rule34.xxx", "www.rule34.xxx",
    "e-hentai.org", "www.e-hentai.org",
    "nhentai.net", "www.nhentai.net",
    "motherless.com", "www.motherless.com",
    "eporner.com", "www.eporner.com",
    "beeg.com", "www.beeg.com",
    "txxx.com", "www.txxx.com",
    "naughtyamerica.com", "www.naughtyamerica.com",
    "realitykings.com", "www.realitykings.com",
    "bangbros.com", "www.bangbros.com",
    "noodlemagazine.com", "www.noodlemagazine.com",
    "whoreshub.com", "www.whoreshub.com",
    "x.com", "www.x.com",
]


class ContentBlocker:
    def __init__(self, db):
        self.db = db
        self.social_blocked = False

    def get_custom_domains(self):
        return self.db.get_custom_blocked_sites()

    def add_custom_domain(self, url):
        domain = url.strip().lower()
        domain = domain.replace("https://", "").replace("http://", "")
        domain = domain.rstrip("/")
        if domain.startswith("www."):
            bare = domain[4:]
        else:
            bare = domain
            domain = "www." + domain
        self.db.add_custom_blocked_site(bare)
        content = self._read_hosts()
        content = self._add_entries(content, [bare, domain], "CUSTOM")
        self._write_hosts(content)
        return bare

    def remove_custom_domain(self, domain):
        self.db.remove_custom_blocked_site(domain)
        content = self._read_hosts()
        lines = content.split("\n")
        filtered = [l for l in lines if not (f"{MARKER}-CUSTOM" in l and domain in l)]
        content = "\n".join(filtered)
        self._write_hosts(content)

    def apply_custom_blocks(self):
        domains = self.db.get_custom_blocked_sites()
        if not domains:
            return
        all_domains = []
        for d in domains:
            all_domains.append(d)
            if not d.startswith("www."):
                all_domains.append("www." + d)
        content = self._read_hosts()
        content = self._remove_entries(content, "CUSTOM")
        content = self._add_entries(content, all_domains, "CUSTOM")
        self._write_hosts(content)

    def _read_hosts(self):
        try:
            with open(HOSTS_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except (PermissionError, FileNotFoundError):
            return ""

    def _write_hosts(self, content):
        try:
            with open(HOSTS_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            os.system("ipconfig /flushdns >nul 2>&1")
            return True
        except PermissionError:
            return False

    def _remove_entries(self, content, tag):
        lines = content.split("\n")
        filtered = [l for l in lines if f"{MARKER}-{tag}" not in l]
        return "\n".join(filtered)

    def _add_entries(self, content, domains, tag):
        new_lines = []
        for domain in domains:
            entry = f"127.0.0.1 {domain} {MARKER}-{tag}"
            if entry not in content:
                new_lines.append(entry)
        if new_lines:
            content = content.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n"
        return content

    # --- Porn blocking (permanent) ---

    def apply_porn_blocks(self):
        if self.db.get_setting("porn_blocking") != "true":
            return
        content = self._read_hosts()
        content = self._remove_entries(content, "PORN")
        content = self._add_entries(content, ADULT_DOMAINS, "PORN")
        self._write_hosts(content)

    def remove_porn_blocks(self):
        content = self._read_hosts()
        content = self._remove_entries(content, "PORN")
        self._write_hosts(content)

    # --- Social media blocking (limit-based) ---

    def apply_social_blocks(self):
        if self.social_blocked:
            return
        content = self._read_hosts()
        content = self._remove_entries(content, "SOCIAL")
        content = self._add_entries(content, SOCIAL_MEDIA_DOMAINS, "SOCIAL")
        if self._write_hosts(content):
            self.social_blocked = True

    def remove_social_blocks(self):
        content = self._read_hosts()
        content = self._remove_entries(content, "SOCIAL")
        if self._write_hosts(content):
            self.social_blocked = False

    def is_social_blocked(self):
        return self.social_blocked

    def get_blocked_domains(self):
        content = self._read_hosts()
        blocked = {"social": [], "porn": []}
        for line in content.split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                if f"{MARKER}-SOCIAL" in line:
                    blocked["social"].append(parts[1])
                elif f"{MARKER}-PORN" in line:
                    blocked["porn"].append(parts[1])
        return blocked
