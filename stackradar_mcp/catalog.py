"""Tool catalog copied from StackRadar's single source of truth.

The web app keeps display, learning, and scrape metadata together in
``backend/app/services/catalog.py``. This server only needs the fields the
scorer and the voice tools use. Slugs, GitHub repos, categories, and keywords
match that file so a mention of "fastapi" lands on the same tool.
"""

from __future__ import annotations

TOOLS: list[dict] = [
    {"name": "React", "slug": "react", "category": "Web Development", "github_repo": "facebook/react", "description": "A JavaScript library for building user interfaces, maintained by Meta.", "keywords": ["react", "reactjs", "react.js"]},
    {"name": "Tailwind CSS", "slug": "tailwindcss", "category": "Web Development", "github_repo": "tailwindlabs/tailwindcss", "description": "A utility-first CSS framework for rapid UI development.", "keywords": ["tailwind", "tailwindcss", "tailwind css"]},
    {"name": "Vite", "slug": "vite", "category": "Web Development", "github_repo": "vitejs/vite", "description": "Frontend build tool with fast hot reload.", "keywords": ["vite", "vitejs"]},
    {"name": "Vue.js", "slug": "vuejs", "category": "Web Development", "github_repo": "vuejs/core", "description": "Progressive JavaScript framework for building web UIs.", "keywords": ["vue", "vuejs", "vue.js"]},
    {"name": "Svelte", "slug": "svelte", "category": "Web Development", "github_repo": "sveltejs/svelte", "description": "UI framework that compiles components to small JavaScript.", "keywords": ["svelte", "sveltekit"]},
    {"name": "Next.js", "slug": "nextjs", "category": "Web Development", "github_repo": "vercel/next.js", "description": "React framework for server rendering, static sites, and routes.", "keywords": ["next.js", "nextjs"]},
    {"name": "FastAPI", "slug": "fastapi", "category": "Web Development", "github_repo": "fastapi/fastapi", "description": "Python web framework for building APIs.", "keywords": ["fastapi", "fast api"]},
    {"name": "Astro", "slug": "astro", "category": "Web Development", "github_repo": "withastro/astro", "description": "Web framework for content sites, with islands of client JavaScript.", "keywords": ["astro"]},
    {"name": "tRPC", "slug": "trpc", "category": "Web Development", "github_repo": "trpc/trpc", "description": "End-to-end typesafe APIs for TypeScript.", "keywords": ["trpc"]},
    {"name": "Bun", "slug": "bun", "category": "Web Development", "github_repo": "oven-sh/bun", "description": "JavaScript runtime, bundler, and package manager.", "keywords": ["bun", "bunjs"]},
    {"name": "Deno", "slug": "deno", "category": "Web Development", "github_repo": "denoland/deno", "description": "JavaScript and TypeScript runtime with built-in security.", "keywords": ["deno"]},
    {"name": "Prisma", "slug": "prisma", "category": "Data & Databases", "github_repo": "prisma/prisma", "description": "ORM for Node.js and TypeScript.", "keywords": ["prisma"]},
    {"name": "PyTorch", "slug": "pytorch", "category": "AI / ML", "github_repo": "pytorch/pytorch", "description": "Machine learning framework for research and production.", "keywords": ["pytorch", "torch"]},
    {"name": "TensorFlow", "slug": "tensorflow", "category": "AI / ML", "github_repo": "tensorflow/tensorflow", "description": "End-to-end machine learning platform from Google.", "keywords": ["tensorflow"]},
    {"name": "Hugging Face Transformers", "slug": "transformers", "category": "AI / ML", "github_repo": "huggingface/transformers", "description": "Library of pretrained transformer models.", "keywords": ["huggingface", "transformers", "hugging face"]},
    {"name": "LangChain", "slug": "langchain", "category": "AI / ML", "github_repo": "langchain-ai/langchain", "description": "Toolkit for building applications on language models.", "keywords": ["langchain"]},
    {"name": "Ollama", "slug": "ollama", "category": "AI / ML", "github_repo": "ollama/ollama", "description": "Run large language models locally.", "keywords": ["ollama"]},
    {"name": "Supabase", "slug": "supabase", "category": "Cloud Native", "github_repo": "supabase/supabase", "description": "Open source backend with Postgres, auth, and APIs.", "keywords": ["supabase"]},
    {"name": "Terraform", "slug": "terraform", "category": "Cloud Native", "github_repo": "hashicorp/terraform", "description": "Infrastructure as code for cloud resources.", "keywords": ["terraform"]},
    {"name": "Kubernetes", "slug": "kubernetes", "category": "Cloud Native", "github_repo": "kubernetes/kubernetes", "description": "Container orchestration system.", "keywords": ["kubernetes", "k8s"]},
    {"name": "Docker", "slug": "docker", "category": "DevOps", "github_repo": "moby/moby", "description": "Build, share, and run containers.", "keywords": ["docker", "dockerfile"]},
    {"name": "Grafana", "slug": "grafana", "category": "DevOps", "github_repo": "grafana/grafana", "description": "Dashboards for metrics, logs, and traces.", "keywords": ["grafana"]},
    {"name": "Prometheus", "slug": "prometheus", "category": "DevOps", "github_repo": "prometheus/prometheus", "description": "Metrics monitoring and alerting toolkit.", "keywords": ["prometheus"]},
    {"name": "Rust", "slug": "rust", "category": "Systems Programming", "github_repo": "rust-lang/rust", "description": "Memory-safe systems language.", "keywords": ["rust", "rustlang"]},
    {"name": "Go", "slug": "go", "category": "Systems Programming", "github_repo": "golang/go", "description": "Compiled language used widely for cloud infrastructure.", "keywords": ["golang", "go lang"]},
    {"name": "Wireshark", "slug": "wireshark", "category": "Cybersecurity", "github_repo": "wireshark/wireshark", "description": "Network protocol analyzer.", "keywords": ["wireshark"]},
    {"name": "Metasploit", "slug": "metasploit", "category": "Cybersecurity", "github_repo": "rapid7/metasploit-framework", "description": "Penetration testing framework.", "keywords": ["metasploit"]},
    {"name": "OWASP ZAP", "slug": "owasp-zap", "category": "Cybersecurity", "github_repo": "zaproxy/zaproxy", "description": "Web application security scanner.", "keywords": ["owasp zap", "owasp-zap", "zaproxy"]},
    {"name": "Hardhat", "slug": "hardhat", "category": "Web3 / Blockchain", "github_repo": "NomicFoundation/hardhat", "description": "Ethereum development environment.", "keywords": ["hardhat"]},
    {"name": "Foundry", "slug": "foundry", "category": "Web3 / Blockchain", "github_repo": "foundry-rs/foundry", "description": "Solidity toolkit written in Rust.", "keywords": ["foundry"]},
    {"name": "Ethers.js", "slug": "ethersjs", "category": "Web3 / Blockchain", "github_repo": "ethers-io/ethers.js", "description": "Library for talking to Ethereum from JavaScript.", "keywords": ["ethers.js", "ethersjs", "ethers"]},
]

TOOLS_BY_SLUG = {tool["slug"]: tool for tool in TOOLS}

# Spoken aliases that are too short or too ambiguous to use as mention keywords.
# "go" is the important one: the web app refuses it as a keyword so "going"
# does not count as the Go language.
ALIASES = {
    "next": "nextjs",
    "nextjs": "nextjs",
    "tailwind": "tailwindcss",
    "vue": "vuejs",
    "go": "go",
    "golang": "go",
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "hf": "transformers",
    "hugging face": "transformers",
    "huggingface": "transformers",
    "zap": "owasp-zap",
    "ethers": "ethersjs",
    "tf": "terraform",
    "pytorch": "pytorch",
    "torch": "pytorch",
}

CATEGORY_ALIASES = {
    "all": None,
    "any": None,
    "web": "Web Development",
    "web development": "Web Development",
    "frontend": "Web Development",
    "front end": "Web Development",
    "data": "Data & Databases",
    "database": "Data & Databases",
    "databases": "Data & Databases",
    "data & databases": "Data & Databases",
    "ai": "AI / ML",
    "ml": "AI / ML",
    "ai/ml": "AI / ML",
    "ai / ml": "AI / ML",
    "machine learning": "AI / ML",
    "cloud": "Cloud Native",
    "cloud native": "Cloud Native",
    "devops": "DevOps",
    "systems": "Systems Programming",
    "systems programming": "Systems Programming",
    "security": "Cybersecurity",
    "cybersecurity": "Cybersecurity",
    "web3": "Web3 / Blockchain",
    "blockchain": "Web3 / Blockchain",
    "web3 / blockchain": "Web3 / Blockchain",
}

SPOKEN_CATEGORY = {
    "Web Development": "web",
    "Data & Databases": "data",
    "AI / ML": "AI and ML",
    "Cloud Native": "cloud",
    "DevOps": "DevOps",
    "Systems Programming": "systems programming",
    "Cybersecurity": "security",
    "Web3 / Blockchain": "Web3",
}

WINDOW_ALIASES = {
    "24h": "24h",
    "24hr": "24h",
    "1d": "24h",
    "day": "24h",
    "today": "24h",
    "daily": "24h",
    "7d": "7d",
    "week": "7d",
    "weekly": "7d",
    "this week": "7d",
    "30d": "30d",
    "month": "30d",
    "monthly": "30d",
    "this month": "30d",
}

WINDOW_SECONDS = {"24h": 86400, "7d": 7 * 86400, "30d": 30 * 86400}
WINDOW_SPOKEN = {"24h": "the last day", "7d": "the last 7 days", "30d": "the last 30 days"}
REDDIT_TIME = {"24h": "day", "7d": "week", "30d": "month"}


def categories() -> list[str]:
    seen: list[str] = []
    for tool in TOOLS:
        if tool["category"] not in seen:
            seen.append(tool["category"])
    return seen
