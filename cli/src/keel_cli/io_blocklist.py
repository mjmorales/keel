"""Per-language I/O package blocklists for pure-logic constraint enforcement."""

BLOCKLISTS: dict[str, frozenset[str]] = {
    "go": frozenset(
        {
            "net",
            "net/http",
            "os",
            "os/exec",
            "os/signal",
            "io",
            "io/fs",
            "io/ioutil",
            "bufio",
            "database/sql",
            "syscall",
            "log",
            "log/slog",
            "plugin",
        }
    ),
    "python": frozenset(
        {
            "os",
            "io",
            "sys",
            "socket",
            "http",
            "http.client",
            "http.server",
            "urllib",
            "urllib3",
            "requests",
            "aiohttp",
            "httpx",
            "pathlib",
            "shutil",
            "tempfile",
            "subprocess",
            "sqlite3",
            "psycopg2",
            "pymongo",
            "redis",
            "asyncio",
            "aiofiles",
            "boto3",
            "grpc",
            "logging",
        }
    ),
    "typescript": frozenset(
        {
            "fs",
            "fs/promises",
            "net",
            "http",
            "https",
            "http2",
            "child_process",
            "dgram",
            "tls",
            "dns",
            "cluster",
            "worker_threads",
        }
    ),
    "rust": frozenset(
        {
            "std::fs",
            "std::net",
            "std::io",
            "std::process",
            "tokio",
            "hyper",
            "reqwest",
            "sqlx",
            "diesel",
            "tracing",
            "log",
        }
    ),
}


def is_io_import(language: str, package: str) -> bool:
    """Check if a package name is an I/O package for the given language."""
    blocklist = BLOCKLISTS.get(language.lower(), frozenset())
    for blocked in blocklist:
        if (
            package == blocked
            or package.startswith(blocked + ".")
            or package.startswith(blocked + "/")
            or package.startswith(blocked + "::")
        ):
            return True
    return False
