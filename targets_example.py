"""Target config for the harvest sitemap scraper.
Copy to targets.py and edit. Entries: (name, sitemap_url,
path_filter_or_None, max_pages). If you inline TARGETS into
scrape-langs.py instead, the __main__ block must stay AFTER every
TARGETS definition or targets are silently skipped.
"""

TARGETS = [
    # Core languages
    ("python", "https://docs.python.org/3/sitemap.xml", None, 15000),
    ("rust", "https://doc.rust-lang.org/sitemap.xml", None, 10000),
    ("go", "https://go.dev/sitemap.xml", r"/doc|/pkg|/blog", 8000),
    ("typescript", "https://www.typescriptlang.org/sitemap.xml", r"/docs|/handbook", 6000),
    ("swift", "https://docs.swift.org/sitemap.xml", None, 5000),
    ("clojure", "https://clojure.org/sitemap.xml", None, 3000),
    ("elixir", "https://hexdocs.pm/sitemap.xml", None, 8000),
    ("julia", "https://docs.julialang.org/sitemap.xml", None, 5000),
    ("haskell", "https://www.haskell.org/sitemap.xml", None, 3000),
    ("ocaml", "https://ocaml.org/sitemap.xml", None, 3000),
    ("nim", "https://nim-lang.org/sitemap.xml", None, 2000),
    ("zig", "https://ziglang.org/sitemap.xml", None, 2000),
    ("erlang", "https://www.erlang.org/sitemap.xml", None, 3000),
    ("perl", "https://perldoc.perl.org/sitemap.xml", None, 5000),
    ("r-lang", "https://cran.r-project.org/sitemap.xml", None, 3000),
    ("lua", "https://www.lua.org/sitemap.xml", None, 2000),
    ("pascal", "https://www.freepascal.org/sitemap.xml", None, 2000),
    ("fortran", "https://fortran-lang.org/sitemap.xml", None, 2000),
    ("prolog", "https://www.swi-prolog.org/sitemap.xml", None, 3000),
    ("scheme", "https://schemers.org/sitemap.xml", None, 1000),
    # Java ecosystem
    ("java", "https://docs.oracle.com/en/java/javase/21/sitemap.xml", None, 8000),
    ("jakarta-ee", "https://jakarta.ee/sitemap.xml", None, 4000),
    ("groovy-lang", "https://groovy-lang.org/sitemap.xml", None, 3000),
    ("grails", "https://docs.grails.org/sitemap.xml", None, 3000),
    # C/C++
    ("cpp", "https://en.cppreference.com/sitemap.xml", None, 15000),
    # Ruby / Rails
    ("ruby-lang", "https://ruby-doc.org/sitemap.xml", None, 5000),
    ("rails", "https://guides.rubyonrails.org/sitemap.xml", None, 5000),
    # Parser / codegen tools
    ("antlr", "https://www.antlr.org/sitemap.xml", None, 2000),
    ("javacc", "https://javacc.github.io/javacc/sitemap.xml", None, 1000),
    ("mvel", "https://mvel.documentnode.com/sitemap.xml", None, 1000),
    ("lex-yacc", "https://www.gnu.org/software/bison/manual/html_node/sitemap.xml", None, 2000),
    # Delphi / Object Pascal
    ("delphi", "https://docwiki.embarcadero.com/sitemap.xml", None, 5000),
    # BeanShell
    ("beanshell", "https://www.beanshell.org/sitemap.xml", None, 1000),
    # Shells
    ("bash", "https://www.gnu.org/software/bash/manual/sitemap.xml", None, 3000),
    ("zsh", "https://zsh.sourceforge.io/sitemap.xml", None, 3000),
    ("csh", "https://www.tcsh.org/sitemap.xml", None, 1000),
    ("ksh", "https://ksh.sourceforge.io/sitemap.xml", None, 2000),
    ("fish", "https://fishshell.com/sitemap.xml", None, 2000),
    # Text processing
    ("awk", "https://www.gnu.org/software/gawk/manual/sitemap.xml", None, 2000),
    ("sed", "https://www.gnu.org/software/sed/manual/sitemap.xml", None, 2000),
    # Spring (full reference, not just the repo adoc)
    ("spring-boot-ref", "https://docs.spring.io/spring-boot/reference/sitemap.xml", None, 10000),
    ("spring-framework-ref", "https://docs.spring.io/spring-framework/reference/sitemap.xml", None, 10000),
    # Unix/Linux commands and coreutils
    ("coreutils", "https://www.gnu.org/software/coreutils/manual/sitemap.xml", None, 3000),
    ("man7", "https://man7.org/sitemap.xml", None, 3000),
    ("linux-man-pages", "https://www.kernel.org/doc/man-pages/sitemap.xml", None, 2000),
    ("util-linux", "https://util-linux.sourceforge.net/sitemap.xml", None, 2000),
    ("findutils", "https://www.gnu.org/software/findutils/manual/sitemap.xml", None, 2000),
    ("grep", "https://www.gnu.org/software/grep/manual/sitemap.xml", None, 1500),
    ("make", "https://www.gnu.org/software/make/manual/sitemap.xml", None, 2000),
    ("gdb", "https://sourceware.org/gdb/sitemap.xml", None, 3000),
    ("git", "https://git-scm.com/sitemap.xml", None, 5000),
    # Toolchain / OS docs
    ("gcc", "https://gcc.gnu.org/sitemap.xml", None, 5000),
    ("freebsd-handbook", "https://docs.freebsd.org/sitemap.xml", None, 5000),
    ("dragonflybsd", "https://www.dragonflybsd.org/sitemap.xml", None, 2000),
    ("openbsd", "https://www.openbsd.org/sitemap.xml", None, 3000),
    ("netbsd", "https://www.netbsd.org/sitemap.xml", None, 3000),
]

# Atlassian / Notion / Google Workspace docs
TARGETS += [
    ("trello", "https://developer.atlassian.com/cloud/trello/sitemap.xml", None, 5000),
    ("notion", "https://developers.notion.com/sitemap.xml", None, 3000),
    ("google-workspace", "https://developers.google.com/sitemap.xml", r"/workspace|/gmail|/sheets|/drive|/calendar|/docs", 10000),
    ("atlassian-dev", "https://developer.atlassian.com/sitemap.xml", None, 8000),
]
# CI/CD, artifact management, config management docs
TARGETS += [
    ("jenkins", "https://www.jenkins.io/sitemap.xml", None, 5000),
    ("sonarqube", "https://docs.sonarsource.com/sonarqube-server/sitemap-pages.xml", None, 8000),
    ("sonarqube-cloud", "https://docs.sonarsource.com/sonarqube-cloud/sitemap-pages.xml", None, 3000),
    ("nexus", "https://help.sonatype.com/sitemap.xml", None, 5000),
    ("artifactory", "https://www.jfrog.com/confluence/sitemap.xml", None, 5000),
    ("slack-api", "https://api.slack.com/sitemap.xml", None, 3000),
    ("puppet", "https://puppet.com/sitemap.xml", r"/docs|/puppet", 5000),
    ("chef", "https://docs.chef.io/sitemap.xml", None, 3000),
    ("salt", "https://docs.saltproject.io/sitemap.xml", None, 3000),
]
# CPU/SoC documentation
TARGETS += [
    ("arm-architecture", "https://developer.arm.com/sitemap.xml", r"/documentation|/architectures|/processor", 5000),
    ("raspberrypi-docs", "https://www.raspberrypi.com/sitemap_index.xml", r"/documentation|/computers", 3000),
    ("intel-sdm", "https://www.intel.com/sitemap.xml", r"/sdm|/software-developer-manual|/isa-extensions|/architecture-instruction-set", 3000),
]
# University course sites (2026-11-23 requests: MIT, Stanford, Harvard)
TARGETS += [
    ("mit-ocw", "https://ocw.mit.edu/sitemap.xml", None, 15000),
    ("harvard-online", "https://pll.harvard.edu/sitemap.xml", None, 5000),
]

# Tech publications / news sites (2026-11-23 request)
TARGETS += [
    ("slashdot", "https://slashdot.org/sitemap-slashdot-index.xml", None, 8000),
    ("arstechnica", "https://arstechnica.com/sitemap.xml", None, 8000),
    ("theregister", "https://www.theregister.com/sitemapindex.xml", None, 8000),
    ("techcrunch", "https://techcrunch.com/sitemap.xml", None, 8000),
    ("wired", "https://www.wired.com/sitemap.xml", None, 8000),
    ("theverge", "https://www.theverge.com/sitemaps", None, 8000),
    ("zdnet", "https://www.zdnet.com/sitemap-google-news.xml", None, 5000),
    ("phoronix", "https://www.phoronix.com/sitemap.php", None, 8000),
]

# Science / math (2026-11-23 request: math, physics, chemistry, science, quantum)
TARGETS += [
    ("libretexts-math", "https://math.libretexts.org/sitemap.xml", None, 10000),
    ("libretexts-chem", "https://chem.libretexts.org/sitemap.xml", None, 10000),
    ("libretexts-phys", "https://phys.libretexts.org/sitemap.xml", None, 8000),
    ("libretexts-bio", "https://bio.libretexts.org/sitemap.xml", None, 8000),
    ("proofwiki", "https://proofwiki.org/sitemap/sitemap-index-proofwik_wiki.xml", None, 8000),
]

# ML / AI (2026-11-23 request)
TARGETS += [
    ("huggingface-docs", "https://huggingface.co/docs/sitemap.xml", None, 8000),
    ("pytorch-docs", "https://docs.pytorch.org/docs/stable/sitemap.xml", None, 5000),
]


# WebMD (2026-11-23)
TARGETS += [
    ("webmd", "https://www.webmd.com/sitemapxml/sitemap.xml", None, 10000),
]

# Medical sites (2026-11-23)
TARGETS += [
    ("medlineplus", "https://medlineplus.gov/sitemap.xml", None, 10000),
    ("clevelandclinic", "https://my.clevelandclinic.org/sitemap.xml", None, 10000),
    ("who", "https://www.who.int/sitemaps/sitemapindex.xml", None, 10000),
    ("healthline", "https://www.healthline.com/sitemap.xml", None, 10000),
]
