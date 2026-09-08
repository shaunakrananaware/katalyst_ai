"""Key-fact smoke tests against the actual Gemini agent, including conversation turns."""

CASES = [
    {
        "name": "point lookup",
        "turns": ["What's happening with the Figma - Enterprise Plan deal?"],
        "facts": [["figma"], ["120000", "120k"], ["lost"], ["budget"]],
    },
    {
        "name": "most recent close",
        "turns": ["Did we close the last deal, and what was the final amount?"],
        "facts": [["notion"], ["96000", "96k"], ["won", "signed"]],
    },
    {
        "name": "meeting and failure",
        "turns": [
            "What happened in the last meeting for Figma - Enterprise Plan, and why did it fail?"
        ],
        "facts": [["budget"], ["vp", "vice president"], ["note-1-2", "email-1-2"]],
    },
    {
        "name": "prospect ranking",
        "turns": ["Top 5 deals by amount in prospect"],
        "facts": [
            ["vercel"],
            ["110000", "110k"],
            ["figma"],
            ["64000", "64k"],
            ["two", "2"],
        ],
        "ordered": ["vercel", "figma"],
    },
    {
        "name": "comparative lessons",
        "turns": [
            "What's the difference between the last 5 closed-won vs closed-lost deals — lessons to learn?"
        ],
        "facts": [
            ["sponsor", "champion"],
            ["budget"],
            ["security", "encryption"],
            ["three", "3"],
        ],
    },
    {
        "name": "ambiguous organization",
        "turns": ["What's happening with Acme?"],
        "facts": [["acme cloud"], ["acme labs"], ["which"]],
        "ambiguous": True,
    },
    {
        "name": "clarification follow-up",
        "turns": ["What's happening with Acme?", "the second one"],
        "facts": [["acme labs"], ["48000", "48k"], ["lost"]],
    },
    {
        "name": "organization people",
        "turns": ["Who works at Linear and what deals are they involved in?"],
        "facts": [["priya shah"], ["revenue insights"]],
    },
    {
        "name": "security loss",
        "turns": ["Why did Acme Cloud - Revenue Platform lose?"],
        "facts": [["security", "encryption"], ["84000", "84k"], ["keys", "residency"]],
    },
    {
        "name": "improvised temporal",
        "turns": [
            "Show the two most recently won deals, newest first, including amounts."
        ],
        "facts": [["notion"], ["96000", "96k"], ["linear"], ["72000", "72k"]],
        "ordered": ["notion", "linear"],
    },
]
