"""Local, unmoderated agent for tradecraft/OSINT activities.

A minimal tool-using loop on a local uncensored model (Ollama, abliterated 14b). Its first job
is the tradecraft activities — analyze material the cloud refuses — with the detector as a tool.
Designed so a richer persona (a local 'gorrie') can drop in as the system prompt + toolset later.
"""

__version__ = "0.1.0"
