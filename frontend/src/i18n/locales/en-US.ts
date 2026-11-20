export default {
  nativeAgent: {
    executionMode: 'Execution mode',
    executionSync: 'Synchronous',
    executionAsync: 'Background async',
    asyncUnavailable: 'Background execution requires a connected Agent Protocol service. Select synchronous mode before saving.',
    asyncOptionsHelp: 'Async supports update_strategy (interrupt or enqueue, default interrupt) and mode (isolated or fork, default isolated). Fork is experimental and copies the parent conversation. Remove these fields before switching to synchronous mode.',
    imageModelHelp: 'Images use the selected vision model, or inherit a main model that supports images.',
    skillsHelp: 'Select instructions, references and scripts from the catalog. A catalog entry does not prove dependencies are installed.',
    runtimeHelp: 'Available execution environments provide a shell; no-shell mode keeps session files. Unavailable legacy bindings remain visible.',
    noShell: 'Session files (no shell)',
    configTitle: 'Native agent configuration',
    subagents: 'Specialist subagents',
    subagentsHelp: 'Declare up to 20 specialists. Omitted model, instructions and access inherit. Omitted or null tools/skills inherit; [] disables them. Omitted/null structured output means normal output.',
    newSubagent: 'New subagent',
    inheritParent: 'Inherit parent',
    childOptions: 'Tools, skills and policies (JSON)',
    childOptionsHelp: 'Optional: allowed_tools, selected_skills, access_level, response_format, permissions, interrupt_on. Child file rules only add denials.',
    addSubagent: 'Add subagent',
    advancedConfig: 'Output and policies',
    responseFormat: 'Structured output (JSON Schema)',
    responseFormatHelp: 'Enter a JSON Schema object, or null for normal output. Only local references are accepted. The server validates the full schema.',
    permissions: 'File permission rules (JSON)',
    permissionsHelp: 'Rules use operations (read/write), absolute paths, and mode (allow/deny/interrupt). They apply to file tools. Sandbox execution paths do not support these rules; platform authorization remains the upper limit.',
    interruptOn: 'Tool approvals (JSON)',
    interruptOnHelp: 'Map tool names to true/false or allowed_decisions (approve/edit/reject/respond), description. Edited arguments use the tool schema. Required platform approvals cannot be disabled.',
    invalidJson: 'Enter valid JSON.',
    interruptTitle: 'Agent waiting for a response',
    responseSchema: 'Response schema',
    responseJson: 'JSON response',
    submitResponse: 'Submit response',
    waitingResponse: 'Waiting for review',
    responseSubmitted: 'Response submitted',
    responseFailed: 'Failed to submit response',
    toolResponse: 'Text to return as the tool result',
    editAndRun: 'Edit and run',
    respondWithoutRun: 'Return text result',
    structuredResult: 'Structured result'
  },
  automation: {
    conversationNotice: 'This conversation is run by an automation. Manual messages are unavailable; handle pending requests above.'
  },
  toolbox: {
    title: 'Toolbox',
    unavailable: 'No tools are available in the current workspace.'
  },
  localBrowser: {
    pipOpen: 'Pop out preview',
    pipReturn: 'Return to conversation',
    pipFailed: 'Could not open the floating window. Please try again.',
    captureScreenshot: 'Capture screenshot',
    navigationIncomplete: 'Navigation did not reach the requested loading phase. Check the current page.',
    noEntries: 'No entries returned.',
    stopping: 'Ending task…',
    elapsedSeconds: '{seconds} s',
    searchInstructionsTitle: 'Browser search instructions',
    searchInstructionsDescription: 'Set your preferred search engine and search URL.',
    searchInstructionsHint: 'Applies to your next request. Leave empty to use the default.',
    searchInstructionsReset: 'Restore default',
    searchInstructionsSaved: 'Saved',
    sourceHint: 'Use the local browser to look up and interact with pages this turn, alongside web search, knowledge bases and other tools.',
    pressKey: 'Press key',
    hoverPage: 'Hover over element',
    scrollPage: 'Scroll page',
    focusElement: 'Focus element',
    blurElement: 'Remove focus',
    selectOption: 'Select option',
    closeTab: 'Close tab',
    runScript: 'Run page script',
    readConsole: 'Read console',
    readNetwork: 'Inspect network requests',
    resizeWindow: 'Resize window',
    emulateDevice: 'Emulate device',
    actionPending: 'Operating browser…',
    actionRecorded: 'Browser action recorded',
    untitledTab: 'Untitled tab',
    contentTruncated: 'Only part of the page content is shown.',
    controlScope: 'Controls this conversation’s browser only',
    pauseHint: 'Interrupt the browser action and keep the pages for resuming. The conversation continues.',
    stopHint: 'Close tabs created by this task and return borrowed tabs. Keep the browser open and paired.',
    openPage: 'Open page',
    switchPage: 'Switch page',
    readPage: 'Read page',
    listTabs: 'List tabs',
    clickPage: 'Click element',
    fillPage: 'Fill content',
    waitPage: 'Wait for page',
    openTab: 'Create task tab',
    switchTab: 'Switch task tab',
    authorizeTab: 'Request tab permission',
    returnTab: 'Return tab',
    needHelp: 'Needs your input',
    browserAction: 'Browser action',
    actionFailed: 'Incomplete',
    actionCompleted: 'Action completed',
    commandBusy: 'The previous browser command is still running. Wait before continuing.',
    invalidArguments: 'Browser tool arguments are invalid or incomplete. The agent must correct them before proceeding.',
    commandInterrupted: 'The browser action was interrupted. Check the page before resuming from the preview.',
    actionFailedHint: 'The browser action did not finish. Check the page and try again.',
    previewStale: 'Preview has not updated',
    previewIdle: 'Last preview retained',
    previewLive: 'Preview syncing',
    previewLoading: 'Fetching preview',
    borrowHint: 'Switch to the page being borrowed and choose Allow or Deny in the BrowserSkill confirmation. Approval continues automatically. Continue operation only resumes a paused task; it does not approve borrowing.',
    helpHint: 'Open the browser from the preview, complete the requested step, then confirm completion in the browser help overlay.',
    settingsTitle: 'Browser connection',
    settingsDescription: 'Pair BrowserSkill with your local Chrome or Edge to operate real web pages from conversations.',
    openSettings: 'Open browser settings',
    settingsHint: 'Connect BrowserSkill in Toolbox to use your local browser here.',
    unavailable: 'Local browsing is not enabled on this server. Contact your administrator.',
    source: 'Browser source',
    sandbox: 'Sandbox browser',
    local: 'Local browser',
    paused: 'Paused',
    connected: 'Connected',
    disconnected: 'Disconnected',
    resume: 'Resume browser',
    pause: 'Pause browser',
    start: 'Start task',
    stop: 'End browser task',
    resumeShort: 'Resume',
    pauseShort: 'Pause',
    stopShort: 'End',
    pairHint: 'Open Connection settings → Remote connection in the extension, paste the pairing link, and confirm the server. The link is valid for 5 minutes and can be used once.',
    copyPairing: 'Copy pairing link',
    copied: 'Copied',
    windowHint: 'Tasks run in a separate browser Agent Window. Borrowing existing tabs requires your permission.',
    preview: 'Local browser task preview',
    waiting: 'Waiting for a task page',
    startHint: 'A browser request creates a separate Agent Window.',
    revoke: 'Revoke device access',
    revokeConfirm: 'You will need to pair again before using the local browser.',
    failed: 'Operation failed. Please retry.',
    productDescription: 'An open-source Chrome and Edge extension that lets agents open pages, read content, and take actions in your browser.',
    offline: 'Offline',
    notPaired: 'Not paired',
    lastSeen: 'Last connected',
    readyHint: 'Ready. Return to the conversation and describe your browser task.',
    capabilitiesTitle: 'Your agent can',
    sidebarStatus: 'Show connection status in the sidebar',
    reconnectHint: 'Authorization is saved. Keep your browser and BrowserSkill open to reconnect automatically.',
    replaceDevice: 'Change browser',
    installExtension: 'Install BrowserSkill',
    storeInstall: 'Chrome Web Store',
    edgeStoreInstall: 'Edge Add-ons',
    extensionMinVersion: 'Requires BrowserSkill v{version} or later. Works with Chrome and Edge.',
    extensionOutdated: 'Extension v{current} is out of date. Update to v{version} or later.',
    manualInstall: 'Install manually (alternative)',
    storeInstallHint: 'Install BrowserSkill from the Chrome Web Store or Edge Add-ons, then return here to pair.',
    installHint: 'If the store is unavailable or its version is incompatible, download the matching package and install it manually.',
    downloadExtension: 'Download matching package',
    officialExtension: 'Official extension (Chrome Web Store)',
    installGuide: 'How do I install the downloaded package?',
    pairGuide: 'How do I use the pairing link?',
    pairBrowser: 'Connect this browser',
    packageUnavailable: 'Ask your administrator for the matching extension package; a download is not configured yet.',
    manualCopy: 'Select and copy the link below. It expires in 5 minutes and can be used once.',
    pairingReady: 'Link copied. Paste it in the extension within 5 minutes. Single use only.',
    copyAgain: 'Copy again',
    usageTitle: 'How to use',
    usageStep1Title: 'Install the extension',
    usageStep1Text: 'Unzip the downloaded ZIP, enter chrome://extensions (edge://extensions in Edge) in the address bar, enable Developer mode, choose Load unpacked, and select the extracted extension folder.',
    usageStep2Title: 'Pair this browser',
    usageStep2Text: 'Copy the pairing link into Connection settings → Remote connection in the extension and confirm the server. Pair once for all conversations in this space.',
    usageStep3Title: 'Describe the task in chat',
    usageStep3Text: 'Turn on Local browser in the conversation input bar before sending a web task. Pairing does not enable this option automatically. Tasks run in a separate Agent Window.',
    usageStep4Title: 'Preview, locate, and resume',
    usageStep4Text: 'A small preview appears in the conversation. Click it to find the task tab. Interrupted tasks stay paused after reconnect — resume them from the preview. Existing tabs require your permission.',
    running: 'Running',
    locateWindow: 'Show browser',
    reconnectShort: 'Waiting to reconnect'
  },
  artifactLibrary: {
    title: 'Artifacts',
    subtitle: 'Files your agents generated across all of your conversations',
    typeFilter: 'Filter by type',
    searchPlaceholder: 'Search filenames',
    categories: {
      all: 'All',
      document: 'Documents',
      spreadsheet: 'Spreadsheets',
      presentation: 'Presentations',
      image: 'Images',
      web: 'Web pages',
      data: 'Data'
    },
    groups: {
      today: 'Today',
      yesterday: 'Yesterday',
      last7Days: 'Last 7 days',
      last30Days: 'Last 30 days',
      earlier: 'Earlier'
    },
    total: '{count} files',
    versions: '{count} versions',
    preview: 'Preview',
    delete: 'Delete',
    deleteTitle: 'Delete this file?',
    deleteConfirm: '“{name}” and its stored contents will be permanently deleted. This cannot be undone.',
    deleteConfirmVersions: 'All {count} versions of “{name}” and their stored contents will be permanently deleted. This cannot be undone.',
    deleted: 'File deleted',
    deleteFailed: 'Delete failed, please retry.',
    download: 'Download',
    downloadFailed: 'Download failed. Please try again later.',
    openSession: 'Open conversation',
    untitledSession: 'Untitled conversation',
    loadMore: 'Load more',
    loadFailed: 'Could not load artifacts',
    retry: 'Retry',
    clearFilters: 'Clear filters',
    empty: {
      title: 'No artifacts yet',
      description: 'Ask an agent to produce a report, spreadsheet or slide deck and the files will show up here'
    },
    noMatches: {
      title: 'No matching files',
      description: 'Try a different keyword or file type'
    }
  },
  resourceSort: {
    title: 'Sort',
    updatedTime: 'Updated time',
    updatedTimeDescription: 'Default option.',
    createdTime: 'Created time',
    createdTimeDescription: 'View the newest or earliest created items',
    name: 'Name',
    nameDescription: 'Quickly find an item when you know its name',
    recentlyUpdated: 'Recently updated',
    earliestUpdated: 'Earliest updated',
    recentlyCreated: 'Recently created',
    earliestCreated: 'Earliest created',
    nameAscending: 'A–Z',
    nameDescending: 'Z–A'
  },
  menu: {
    sessionInProgress: 'Conversation in progress',
    sessionUnread: 'New reply',
    knowledgeBase: 'Knowledge Base',
    agents: 'Agents',
    automations: 'Automations',
    artifacts: 'Artifacts',
    organizations: 'Shared Spaces',
    newChat: 'New Chat',
    settings: 'System Settings',
    logout: 'Logout',
    clearMessages: 'Clear Messages',
    clearMessagesSuccess: 'Messages cleared',
    clearMessagesFailed: 'Failed to clear messages, please try again later',
    renameSession: 'Rename',
    renameSessionSuccess: 'Title updated',
    renameSessionFailed: 'Failed to update title, please try again later',
    batchManage: 'Batch Manage',
    newSession: 'New Chat',
    pin: 'Pin',
    unpin: 'Unpin',
    pinFailed: 'Failed to pin, please try again later',
    unpinFailed: 'Failed to unpin, please try again later',
    search: 'Search',
    collapseSidebar: 'Collapse Sidebar',
    expandSidebar: 'Expand Sidebar',
    myChats: 'My chats',
    apiChats: 'API sessions',
    noSessions: 'No conversations yet'
  },
  chatHeader: {
    grants: {
      menu: 'Allowed actions',
      description: 'Actions allowed for this conversation without asking again. Revoke one to be asked next time.',
      empty: 'No allowed actions yet',
      revoke: 'Revoke',
      revoked: 'Revoked',
      revokeFailed: 'Failed to revoke',
      loadFailed: 'Failed to load'
    },
    automationTask: 'Automation',
    moreActions: 'More conversation actions',
    toggleSandboxPanel: 'Sandbox terminal',
    copyMarkdown: 'Copy as Markdown',
    deleteSession: 'Delete Conversation',
    renamePlaceholder: 'Enter a conversation title',
    temporaryWorkspace: 'Temporary workspace',
    markdownCopied: 'Full conversation copied as Markdown',
    markdownCopyFailed: 'Failed to copy Markdown. Please try again.',
    clearConfirmTitle: 'Clear Conversation Messages',
    clearConfirmBody: 'Clear all messages in this conversation? The conversation will remain, but this cannot be undone.',
    deleteConfirmTitle: 'Delete Conversation',
    deleteConfirmBody: 'Delete this conversation? This cannot be undone.',
    deleteSuccess: 'Conversation deleted',
    markdown: {
      sessionId: 'Session ID',
      exportedAt: 'Exported at',
      user: 'User',
      assistant: 'Assistant',
      attachments: 'Attachments',
      references: 'References'
    }
  },
  assistantEntryGuide: {
    stepOf: 'NEW IN v0.9.0',
    skip: 'Got it',
    interactHint: 'Click the highlighted entry to open the assistant.'
  },
  newUserGuide: {
    stepOf: '{current} / {total}',
    skip: 'Skip',
    prev: 'Back',
    next: 'Next',
    done: 'Done',
    reopen: 'Product tour',
    steps: {
      assistant: {
        title: 'Meet the Xiaozhi Assistant',
        desc: 'Ask about Xiaozhi versions, features and setup. Using the current page as context, the assistant can create agents, schedule tasks and organize knowledge on your behalf, within your permissions.'
      },
      welcome: {
        title: 'Welcome to Xiaozhi',
        desc: 'A few quick steps to get you familiar with knowledge bases, chat and agents. Click "Next" to begin.'
      },
      knowledge: {
        title: 'Create your knowledge base',
        desc: 'Everything starts here: upload documents, web pages or FAQs and Xiaozhi parses and indexes them automatically. Click here to open knowledge bases.'
      },
      chat: {
        title: 'Start an AI chat',
        desc: 'Ask questions grounded in your knowledge base and get accurate answers with cited sources. Click here to start a new chat.'
      },
      agents: {
        title: 'Build dedicated agents',
        desc: 'Combine knowledge bases, prompts and tools into reusable agents that capture your expertise.'
      },
      settings: {
        title: 'Account & settings',
        desc: 'Open this to manage your account, members and system settings. You can reopen this tour from the help button next to your name at the top of this menu.'
      },
      models: {
        title: 'Configure your models',
        desc: 'A key step: add chat, embedding and other models in Model Management so knowledge bases and chat can work. Click "Add model" to get started.'
      },
      done: {
        title: 'You are all set',
        desc: 'You now know the essentials — start building your knowledge assistant! Revisit this tour anytime from the help button next to your name in this menu.'
      }
    }
  },
  contextualGuide: {
    stepOf: '{current} / {total}',
    skip: 'Skip',
    prev: 'Back',
    next: 'Next',
    done: 'Got it',
    interactHint: 'Click the highlighted area to continue',
    kbList: {
      steps: {
        create: {
          title: 'Create your first knowledge base',
          desc: 'Knowledge bases hold documents and FAQs. Click the highlighted "New knowledge base" button below and we will walk you through the form.'
        }
      }
    },
    tenantModels: {
      needChatModelFirst: 'Add a chat model (KnowledgeQA) before creating an agent.',
      steps: {
        intro: {
          title: 'Configure models first',
          desc: 'A document knowledge base needs at least one chat model (summaries and Q&A) and one Embedding model (vector search). Add them in system settings.'
        },
        addModel: {
          title: 'Add models',
          desc: 'Click "Add model" and configure KnowledgeQA (chat) and Embedding types. Lite users can pull local models via Ollama.'
        },
        done: {
          title: 'Then continue',
          desc: 'After saving models, close settings and click "New knowledge base". The wizard will walk you through type, indexing, and model binding.'
        }
      },
      stepsAgent: {
        intro: {
          title: 'Configure a chat model first',
          desc: 'Creating an agent requires at least one KnowledgeQA model. Add it in system settings (Embedding is only required for knowledge bases).'
        },
        addModel: {
          title: 'Add a chat model',
          desc: 'Click "Add model" and configure a KnowledgeQA type.'
        },
        done: {
          title: 'Then create an agent',
          desc: 'After saving, close settings and click "Create agent". The wizard covers mode, knowledge bases, and attachment upload options.'
        }
      }
    },
    kbCreate: {
      steps: {
        type: {
          title: 'Choose a type',
          desc: 'Document bases are for PDFs, Word files, and similar uploads. FAQ bases are for question–answer pairs. The type cannot be changed later.'
        },
        name: {
          title: 'Enter a name',
          desc: 'Pick a clear name such as "Product manual" or "Support FAQ". Description is optional.'
        },
        indexing: {
          title: 'Indexing capabilities',
          desc: 'Vector and keyword search are on by default. You can also enable Wiki or knowledge-graph indexing. Keep at least one search mode enabled.'
        },
        navModels: {
          title: 'Model setup (required)',
          desc: 'Every knowledge base needs a chat model; retrieval also requires an Embedding model. Open "Model configuration" on the left.'
        },
        llm: {
          title: 'Chat / summary model',
          desc: 'Used for summaries and answers. If the list is empty, use the dropdown to open settings and add a model.'
        },
        embedding: {
          title: 'Embedding model',
          desc: 'Turns text into vectors for semantic search. Works with vector/keyword indexing above.'
        },
        parser: {
          title: 'Parser engine (optional)',
          desc: 'How PDFs and Office files are parsed. Defaults work for most cases; adjust if you need OCR or special layouts.'
        },
        chunking: {
          title: 'Chunking (optional)',
          desc: 'How documents are split for retrieval. Default chunk sizes are tuned for RAG and rarely need changes.'
        },
        storage: {
          title: 'Storage (optional)',
          desc: 'Where raw files are stored (local or object storage). The workspace default is usually fine.'
        },
        navMultimodal: {
          title: 'Multimodal / images (optional)',
          desc: 'Enable this if documents contain charts, scans, or image-heavy content that needs vision understanding.'
        },
        multimodalToggle: {
          title: 'Enable multimodal parsing',
          desc: 'When on, image-bearing uploads are processed with a vision-language model for better retrieval.'
        },
        multimodalVllm: {
          title: 'Choose a VLM model',
          desc: 'Multimodal requires a VLM. Add one in system settings if the list is empty.'
        },
        faq: {
          title: 'FAQ indexing',
          desc: 'Choose how Q&A pairs are indexed. You can add FAQ entries after creation.'
        },
        submit: {
          title: 'Create the knowledge base',
          desc: 'Click Got it to finish the guide without creating a knowledge base. When ready, enter a name, confirm the type and models, then click Create.'
        }
      }
    },
    agentList: {
      steps: {
        create: {
          title: 'Create your agent',
          desc: 'Agents combine models, knowledge bases, tools, and prompts into reusable assistants. Click the highlighted "Create agent" button.'
        }
      }
    },
    agentCreate: {
      steps: {
        mode: {
          title: 'Choose run mode',
          desc: '"Quick answer" for straightforward Q&A; "Smart reasoning" uses tools and multi-step thinking for complex tasks.'
        },
        agentType: {
          title: 'Choose an agent type',
          desc: 'Presets fill in the system prompt, recommended tools, and knowledge scope (e.g. Wiki builder, data analysis). Switch by scenario—name and description update accordingly.'
        },
        name: {
          title: 'Name and description',
          desc: 'Pick a recognizable name. Smart-reasoning mode may pre-fill a default you can edit.'
        },
        navModel: {
          title: 'Bind a chat model',
          desc: 'Every agent needs a KnowledgeQA model as its reasoning engine.'
        },
        model: {
          title: 'Select model',
          desc: 'Choose from configured chat models, or add one in system settings first.'
        },
        navKnowledge: {
          title: 'Link knowledge bases',
          desc: 'Control which knowledge the agent can retrieve. Default is all knowledge bases.'
        },
        knowledge: {
          title: 'Knowledge scope',
          desc: '"All" for general assistants; "Selected" for a domain; "None" relies on the model alone or web search.'
        },
        navWebsearch: {
          title: 'Web search (optional)',
          desc: 'Allow the agent to call external search for up-to-date information.'
        },
        navMultimodal: {
          title: 'Attachment upload (optional)',
          desc: 'Lets users send images, documents, and audio in chat; image understanding requires a VLM in system settings.'
        },
        multimodal: {
          title: 'Enable attachment upload',
          desc: 'Configure image and audio upload plus attachment parse rules; select a VLM below when image upload is enabled.'
        },
        navTools: {
          title: 'Tools & MCP (optional)',
          desc: 'In smart-reasoning mode, enable built-in tools and MCP services for search, code, and more.'
        },
        submit: {
          title: 'Save the agent',
          desc: 'Click the highlighted confirm button to finish. You can then select this agent in chat.'
        }
      }
    },
    kbDetail: {
      steps: {
        intro: {
          title: 'This knowledge base is empty',
          desc: 'Add your first item so you can search and chat over it. You can also drag and drop supported file types.'
        },
        upload: {
          title: 'Add documents',
          desc: 'Use this menu to upload files or folders, import a URL, or create content online.'
        },
        done: {
          title: 'Ready after parsing',
          desc: 'Once documents are indexed, mention this knowledge base in chat with {\'@\'} to get answers with citations.'
        }
      }
    },
    chat: {
      steps: {
        kb: {
          title: 'Choose knowledge scope',
          desc: 'Click {\'@\'} to pick one or more knowledge bases or files. Answers use only the selection; otherwise the current agent settings apply.'
        },
        input: {
          title: 'Type your question',
          desc: 'Describe what you want to know, or click a suggested question above to get started quickly.'
        },
        send: {
          title: 'Send to start chatting',
          desc: 'Sending creates a new session. The AI answers using your knowledge base and shows cited passages.'
        },
        done: {
          title: 'You are ready to explore',
          desc: 'Try a question related to your uploaded documents and see grounded answers with references.'
        }
      }
    }
  },
  batchManage: {
    selectAll: 'Select All',
    cancel: 'Cancel',
    delete: 'Delete Conversations',
    deleteConfirmTitle: 'Delete Conversations',
    deleteConfirmBody: 'Are you sure you want to delete the selected {count} conversation(s)? This action cannot be undone.',
    deleteAllConfirmBody: 'Are you sure you want to delete all conversations? This action cannot be undone.',
    deleteSuccess: 'Deleted successfully',
    deleteFailed: 'Delete failed, please try again later'
  },
  listSpaceSidebar: {
    all: 'All',
    workspace: 'Workspace',
    spaces: 'Shared with me',
    favorites: 'Starred',
    recents: 'Recent'
  },
  resourceOrigin: {
    mine: 'Mine',
    mineTooltip: 'Created by you',
    tenant: 'Workspace',
    tenantTooltip: 'Created by another member of this workspace',
    tenantTooltipWithCreator: 'Created by {creator}',
    space: 'Space',
    spaceTooltip: 'Shared via space "{space}"',
    spaceTooltipWithTenant: 'Shared via space "{space}" · from {tenant}',
    shared: 'External',
    sharedTooltip: 'Accessed from an external workspace via a shared space'
  },
  knowledgeBase: {
    infoCard: {
      title: 'Knowledge Base Info'
    },
    sort: {
      title: 'Sort'
    },
    folderTree: {
      title: 'Folders',
      rootRow: 'Root'
    },
    moveToFolder: {
      action: 'Move to folder',
      newFolderPlaceholder: 'New folder name',
      newFolderAddRoot: 'New sub-folder under root',
      newFolderAddUnder: 'New sub-folder under “{folder}”',
      duplicate: 'That folder already exists'
    },
    videosFilteredNoVLM: 'Skipped {count} video file(s) (video upload is not supported)',
    importURL: 'Import from URL',
    addDocument: 'Add Document',
    importURLTitle: 'Import from URL',
    urlRequired: 'Please enter a URL',
    invalidURL: 'Please enter a valid URL',
    urlLabel: 'URL Address',
    urlPlaceholder: 'Enter webpage URL, e.g., https://example.com',
    urlTip: 'Supports importing various webpage contents. The system will automatically extract and parse text content from the webpage',
    channelLabel: 'Source Channel',
    channelWeb: 'Web',
    channelApi: 'API',
    channelBrowserExtension: 'Browser Extension',
    channelWechat: 'WeChat',
    channelWecom: 'WeCom',
    channelFeishu: 'Feishu',
    channelDingtalk: 'DingTalk',
    channelSlack: 'Slack',
    channelIm: 'IM Channel',
    channelConfluence: 'Confluence',
    channelGitLab: 'GitLab',
    channelNextcloud: 'Nextcloud',
    channelSeafile: 'Seafile',
    channelIma: 'Tencent IMA',
    channelUnknown: 'Unknown',
    selectedCount: '{count} selected',
    pdfDocFormat: 'pdf, doc format files, max {size}MB',
    textMarkdownFormat: 'text, markdown format files, max {size}MB',
    dragFileNotText: 'Please drag files instead of text or links',
    searchPlaceholder: 'Search knowledge bases...',
    noMatch: 'No matching knowledge base found',
    noKnowledge: 'No knowledge bases available',
    loadingFailed: 'Failed to load knowledge bases',
    allFilesSkippedNoEngine: 'All selected files were skipped due to no available parser engine',
    filesSkippedNoEngine: '{count} file(s) skipped due to no available parser engine'
  },
  uploadConfirm: {
    imageEmbeddingModel: 'Image indexing embedding model',
    imageIndexInherited: 'Image indexing uses the embedding model assigned to this knowledge base. Change it in knowledge base settings.',
    imageVectorIndex: 'Image vector indexing for this import',
    imageVectorIndexHint: 'Generate image vectors for this upload or reparse without changing knowledge base defaults. Retrieval still follows the knowledge base image vector search setting.',
    imageVectorRequiresIndex: 'Enable vector indexing in knowledge base settings first.',
    documentSummary: 'Document summary',
    documentSummaryDescription: 'Choose whether to automatically summarize documents in this import.',
    generateSummary: 'Generate document summaries',
    generateSummaryHint: 'Enabled by default. Disable to skip summaries while parsing, indexing, and other configured steps continue.',
    title: 'Confirm Upload',
    parseConfig: 'Parse settings',
    configNav: 'Parse settings navigation',
    navParserDefault: 'Default',
    navParserCustomized: 'Customized',
    moreOptions: 'More processing options',
    summaryParentChildShort: 'Parent-child',
    summaryParserForceScanned: 'Scanned mode',
    summaryQuestionCountValue: '{count}',
    summaryGraphTagsValue: '{count}',
    navChunkingSummary: 'Chunk {size}',
    statusOn: 'On',
    statusOff: 'Off',
    notSet: 'Not set',
    summaryNoTags: 'Not set',
    summaryTagsCount: '{count} tags',
    confirm: 'Upload and parse',
    cancel: 'Cancel',
    tabTags: 'Document tags',
    tagsDescription: 'Select one or more tags for every document in this import batch',
    tagsPlaceholder: 'Select tags (multiple allowed)',
    tagsEmpty: 'This knowledge base has no tags. You can create them in tag management after upload.',
    tagsLoadFailed: 'Failed to load tags. You can set them later from the document list.',
    noItems: 'Add at least one file or URL',
    urlItemLabel: 'URL',
    urlAdded: 'URL added',
    urlDuplicate: 'This URL is already in the list',
    statusNeedsSetup: 'Needs setup',
    multimodalSetupHint: 'Images detected. Enable multimodal and select a model.',
    asrSetupHint: 'Audio detected. Enable speech recognition and select a model.',
    vlmModelRequired: 'Configure a multimodal model',
    asrModelRequired: 'Configure a speech recognition model',
    vlmModelSelectRequired: 'Multimodal is enabled. Please select a VLM model.',
    asrModelSelectRequired: 'Speech recognition is enabled. Please select an ASR model.',
    pdfForceScanned: {
      label: 'Force scanned PDF parsing',
      description: 'Useful for web-print, scanned, or image-heavy PDFs. Every page will be rendered as an image and processed via OCR/VLM. May increase processing time and model costs.'
    },
    continueAdd: 'Add more',
    destinationLabel: 'Upload location',
    destinationChange: 'Change upload location',
    filesAdded: 'Added {count} file(s)',
    filesAllDuplicate: 'Selected files are already in the list',
    titleManual: 'Confirm online publish',
    confirmManual: 'Publish and parse',
    titleReparse: 'Confirm reparse',
    confirmReparse: 'Confirm and reparse',
    reparseSource: 'Document to reparse',
    reparseHint: 'Reuses the last parse settings; adjust them here',
    manualCharCount: '{count} characters'
  },
  knowledgeStages: {
    processConfig: {
      title: 'Parse config for this run'
    },
    expandBranch: 'Expand children',
    collapseBranch: 'Collapse children',
    resizeDrawer: 'Drag to resize panel width',
    stall: {
      title: 'No progress for {minutes} minutes; this may be stuck'
    },
    stage: {
      docreader: 'Document parsing',
      chunking: 'Chunking',
      embedding: 'Vectorization',
      multimodal: 'Multimodal recognition',
      postprocess: 'Post-processing'
    },
    status: {
      pending: 'Pending',
      running: 'Running',
      finalizing: 'Finalizing',
      done: 'Done',
      failed: 'Failed',
      skipped: 'Skipped',
      cancelled: 'Cancelled'
    }
  },
  agent: {
    taskLabel: 'Task:',
    think: 'Thinking',
    copy: 'Copy',
    addToKnowledgeBase: 'Add to Knowledge Base',
    artifactDrawer: {
      buttonTitle: 'View files generated in this reply',
      title: 'Generated files',
      empty: 'No downloadable files were generated this turn.',
      preview: 'Preview',
      previewBack: 'Back to list',
      collecting: 'Saving generated files…',
      delete: 'Delete',
      deleteTitle: 'Delete this file?',
      deleteConfirm: '“{name}” and its stored contents will be permanently deleted. This cannot be undone.',
      deleted: 'File deleted',
      deleteFailed: 'Delete failed, please retry.',
      download: 'Download',
      downloadFailed: 'Download failed, please retry.',
      inlinePreviewHint: 'Click to preview',
      inlineMissing: 'File unavailable',
      inlineDeleted: 'File deleted'
    },
    updatePlan: 'Update Plan',
    webSearchFound: 'Found <strong>{count}</strong> web search result(s)',
    toolFallback: 'Tool',
    stepsCompleted: 'Completed <strong>{steps}</strong> step(s)',
    reasoningRounds: '<strong>{rounds}</strong> reasoning round(s)',
    earlierSteps: '{count} earlier steps',
    viewReasoning: 'View reasoning',
    toolCalls: '<strong>{tools}</strong> tool call(s)',
    durationSuffix: '<strong>{duration}</strong>',
    stepSummarySeparator: ' · ',
    contextCompacted: 'Compacted context',
    contextCompactedSummary: '{before} → {after} tokens',
    contextCompactedDegraded: 'Summary unavailable, raw transcript kept',
    title: 'Agents',
    subtitle: 'Configure and manage your agents to customize conversation behavior and capabilities',
    createAgent: 'Create Agent',
    builtin: 'Built-in',
    disabled: 'Disabled',
    disable: 'Disable',
    enable: 'Enable',
    noDescription: 'No description',
    selectAgent: 'Select Agent',
    noAgents: 'No agents',
    manageAgents: 'Manage',
    builtinAgents: 'Built-in Agents',
    customAgents: 'Custom Agents',
    capabilities: {
      kbCount: '{count} knowledge base(s) specified',
      kbAll: 'Access to all knowledge bases',
      mcpEnabled: 'MCP services enabled',
      multiTurn: 'Multi-turn conversation'
    },
    type: {
      normal: 'Quick Answer',
      agent: 'Smart Reasoning'
    },
    mode: {
      normal: 'Quick Answer',
      agent: 'Smart Reasoning'
    },
    features: {
      webSearch: 'Web Search Enabled',
      knowledgeBase: 'Knowledge Base Linked',
      mcp: 'MCP Services Enabled',
      multiTurn: 'Multi-turn Conversation'
    },
    tabs: {
      sharedToMe: 'Shared to Me'
    },
    sections: {
      builtin: 'Built-in',
      mine: 'Created by me',
      tenantOthers: 'Workspace · Other members',
      tenantReadonly: 'Workspace · View only',
      sharedByMe: 'Shared by me',
      sharedEditable: 'Shared with me · Can edit',
      sharedReadonly: 'Shared with me · View only'
    },
    empty: {
      title: 'No Custom Agents',
      description: 'Click the button in the top right to create your first agent',
      sharedTitle: 'No shared agents yet',
      sharedDescription: 'You can join a space or ask others to share agents with you',
      favoritesTitle: 'No favorites yet',
      favoritesDescription: 'Star an agent from its card to add it here',
      recentsTitle: 'Nothing here yet',
      recentsDescription: 'Agents you recently used will show up here'
    },
    detail: {
      title: 'Agent Details',
      useInChat: 'Use in Chat'
    },
    shareScope: {
      title: 'Share Scope',
      desc: 'Space members have read-only access to this agent and will use it according to your current configuration; your changes to the agent will sync to shared spaces. To allow space members to edit knowledge base content, share the knowledge base to the space.',
      knowledgeBase: 'Knowledge bases',
      chatModel: 'Chat model',
      rerankModel: 'Rerank model',
      webSearch: 'Web search',
      mcp: 'MCP services',
      kbAll: 'All knowledge bases',
      kbSelected: '{count} selected',
      kbNone: 'None',
      modelConfigured: 'Configured',
      modelNotSet: 'Not set',
      enabled: 'On',
      disabled: 'Off',
      mcpAll: 'All services',
      mcpSelected: '{count} selected',
      mcpNone: 'None'
    },
    delete: {
      confirmTitle: 'Delete Agent',
      confirmMessage: 'Are you sure you want to delete agent "{name}"? This action cannot be undone.'
    },
    messages: {
      created: 'Agent created successfully',
      updated: 'Agent updated successfully',
      deleted: 'Agent deleted',
      deleteFailed: 'Delete failed',
      saveFailed: 'Save failed',
      copied: 'Agent copied successfully',
      copyFailed: 'Copy failed',
      disabled: 'Agent disabled',
      enabled: 'Agent enabled'
    },
    editor: {
      assistantChanged: 'The assistant changed this agent. Reopen it to see the latest settings.',
      assistantDeleted: 'The assistant deleted this agent.',
      reasoningEffortUnsupported: 'The selected model cannot think; every option except "Off" is ignored.',
      reasoningEffortAlwaysOn: 'The selected model always reasons and cannot be switched off; only the effort level can be changed.',
      createTitle: 'Create Agent',
      editTitle: 'Edit Agent',
      buttons: {
        create: 'Create Agent',
        saveAndClose: 'Save and Close'
      },
      postCreateHint: {
        title: 'Created successfully',
        footer: 'Keep adjusting settings, configure sharing and publishing, then click "Save and Close".'
      },
      basicInfo: 'Basic Info',
      basicInfoDesc: 'Configure agent name, description, and run mode',
      nativeRuntime: {
        adoptRuntime: 'Use current runtime settings',
        incompatible: 'Some values are incompatible with this deployment. Review the changes below. Adopting them updates the draft; saving makes them effective.',
        adoptQuick: 'Use current native quick-answer settings',
        changesPending: 'These changes are in the draft and take effect after saving.',
        removed: 'Remove field',
        defaultsUnavailable: 'Current runtime defaults could not be loaded. Reload them before saving.',
        retry: 'Reload',
        resolveBeforeSave: 'Resolve incompatible settings before saving.',
        quickDesc: 'Quick answer uses the native agent to retrieve and answer as needed, with its own model-call limit.',
        promptDesc: 'Configure system instructions or a template reference for the current mode'
      },
      promptsConfig: 'Prompts',
      promptsConfigDesc: 'Configure system, context, intent, rewrite, and fallback prompts',
      modelConfig: 'Model Config',
      modelConfigDesc: 'Configure chat model, auxiliary models (ReRank), and generation parameters',
      toolsConfig: 'Tools',
      toolsConfigDesc: 'Configure tools available to the Agent',
      knowledgeConfig: 'Knowledge Base',
      knowledgeConfigDesc: 'Configure knowledge base scope and FAQ strategy for the agent',
      agentId: 'Agent ID',
      agentIdDesc: 'Use this ID to target the agent in API integrations',
      name: 'Name',
      namePlaceholder: 'Enter agent name',
      nameRequired: 'Agent name is required',
      systemPromptRequired: 'System prompt is required',
      modelRequired: 'Please select a model',
      queryMissingInRewrite: 'Rewrite user prompt must contain {\'{{\'}query{\'}}\'} placeholder',
      queryMissingInFallback: 'Fallback prompt must contain {\'{{\'}query{\'}}\'} placeholder',
      description: 'Description',
      descriptionPlaceholder: 'Enter agent description',
      normalDesc: 'Quick response, direct answers',
      agentDesc: 'Multi-step thinking, deep analysis for complex questions',
      model: 'Model',
      modelPlaceholder: 'Select Model',
      systemPrompt: 'System Prompt',
      systemPromptPlaceholder: 'Custom system prompt to define agent behavior and role (use {\'{{\'}web_search_status{\'}}\'} placeholder for dynamic web search behavior)',
      contextTemplateRequired: 'Context template is required',
      temperature: 'Temperature',
      thinking: 'Thinking Mode',
      citationEnabled: 'Show Source Citations',
      citationEnabledDesc: 'Show knowledge-base and web sources in final answers; retrieval and grounding still work when disabled',
      mode: 'Running Mode',
      knowledgeBases: 'Knowledge Bases',
      allKnowledgeBases: 'All Knowledge Bases',
      selectedKnowledgeBases: 'Selected Knowledge Bases',
      noKnowledgeBase: 'No Knowledge Base',
      selectKnowledgeBases: 'Select Knowledge Bases',
      selectKnowledgeBasesDesc: 'Select knowledge bases to associate (including collaborative ones)',
      myKnowledgeBases: 'My Knowledge Bases',
      sharedKnowledgeBases: 'Collaborative Knowledge Bases',
      retrieveKBOnlyWhenMentioned: 'Retrieve Only When Mentioned',
      retrieveKBOnlyWhenMentionedDesc: 'Off: auto-retrieve configured KBs; On: retrieve only when user {\'@\'} mentions',
      rerankModel: 'ReRank Model',
      rerankModelDesc: 'Used to rerank knowledge base retrieval results for better accuracy',
      rerankModelPlaceholder: 'Select ReRank Model',
      rerankModelOptionalHint: 'No RAG knowledge base in current scope, so this is optional. If a RAG knowledge base is added later, the workspace default rerank model will be used as a fallback. Configuring it explicitly is still recommended.',
      maxIterations: 'Main Agent Model Call Limit',
      maxIterationsLimit: 'Limit',
      maxIterationsUnlimited: 'Unlimited',
      allowedTools: 'Allowed Tools',
      retrievalStrategy: 'Retrieval Strategy',
      contextTemplate: 'Context Template',
      contextTemplatePlaceholder: 'Custom context template...',
      queryUnderstandModel: 'Query Understand Model',
      queryUnderstandModelPlaceholder: 'Leave empty to reuse the main chat model',
      rewritePromptSystem: 'Rewrite System Prompt',
      rewritePromptSystemPlaceholder: 'Leave empty to use default prompt',
      rewritePromptUser: 'Rewrite User Prompt',
      rewritePromptUserPlaceholder: 'Leave empty to use default prompt',
      maxCompletionTokens: 'Max Completion Tokens',
      maxCompletionTokensDefault: 'Default',
      maxCompletionTokensCustom: 'Custom',
      fallbackStrategy: 'Fallback Strategy',
      fallbackResponse: 'Fixed Response',
      fallbackResponsePlaceholder: 'Sorry, I cannot answer this question.',
      fallbackPrompt: 'Fallback Prompt',
      fallbackPromptPlaceholder: 'Leave empty to use default prompt',
      skillsConfig: 'Skills',
      skillsSelection: 'Skill list',
      skillsAll: 'All',
      skillsSelected: 'Selected',
      skillsNone: 'Disabled',
      skillsGroupUnavailable: 'Unavailable',
      noSkillsAvailable: 'The workspace catalog has no skills yet.',
      goSandboxSettings: 'Manage sandboxes',
      sandboxBackend: 'Sandbox',
      memoryEnabled: 'Long-term Memory'
    },
    selector: {
      title: 'Select Agent',
      current: 'Current',
      goToSettings: 'Settings',
      sharedLabel: 'Shared',
      notReadyHint: 'Not ready. Configure: {items}',
      notReadyStatus: 'Setup needed',
      configureAction: 'Configure',
      sharedNotReadyContact: 'Ask the sharing organization admin to finish setup',
      capabilitiesSection: 'Capabilities',
      webSearchCapability: 'Web search',
      imageUploadCapability: 'Image upload',
      capabilityEnabled: 'On',
      capabilityDisabled: 'Off',
      capabilitySupported: 'Supported',
      capabilityUnsupported: 'Unsupported',
      capabilityUnconfigured: 'Not set'
    }
  },
  settings: {
    modelManagement: 'Model Management',
    autoCheckUpdate: 'Auto Download Updates',
    autoCheckUpdateDesc: 'When enabled, automatically check and download the latest version in the background.',
    parserEngine: 'Parser Engine',
    sandbox: {
      title: 'Sandbox Config',
      skillUploadClick: 'Click to upload a zip bundle',
      skillUploadDrag: 'or drop a file here',
      skillSourceSection: 'Install from a source',
      skillSourceSectionHint: 'Paste a ClawHub, GitHub or SkillHub link, or {\'@\'}owner/slug. The bundle cannot exceed {size} MB.',
      skillUploadSection: 'Upload a local bundle',
      skillUploadSectionHint: 'Drop a zip that contains SKILL.md below, or click to pick a file. The bundle cannot exceed {size} MB.',
      skillSourcePlaceholder: 'ClawHub: {\'@\'}owner/slug. GitHub/SkillHub: paste the full URL',
      skillSourceFailed: 'Failed to install the skill from the registry',
      skillUploadFailed: 'Failed to upload the skill',
      skillBundleTooLarge: 'The skill bundle cannot exceed {size} MB.',
      skillBundleTooManyFiles: 'The skill directory cannot hold more than {count} files.',
      skillBundleTooManyZipEntries: 'The archive cannot have more than {count} zip entries.',
      installCommandRunning: 'Command running',
      skillFiles: 'View files',
      skillFilesTitle: 'Files',
      skillFilesEmpty: 'This skill has no files to browse yet.',
      skillFilesLoadFailed: 'Failed to load skill files',
      skillFilesFileLoadFailed: 'Could not read this file',
      skillFilesBinary: 'This file is binary and cannot be previewed.',
      skillFilesTruncated: 'The file is large; only the beginning is shown.',
      skillFilesSelectHint: 'Select a file on the left to view it',
      skillFilesPreview: 'Preview',
      skillFilesSource: 'Source',
      skillDisabled: 'Skill disabled',
      installCommandWaiting: 'Waiting for command output. Elapsed time continues to update.'
    },
    skills: {
      nativeUsage: 'Select packages in the agent configuration. Scripts require OpenSandbox and suitable dependencies; a catalog entry does not prove dependencies are installed.',
      addSourceDescription: 'Import a directory containing one SKILL.md, references and scripts. Importing records content and does not execute an installer.',
      title: 'Skill Management',
      description: 'Manage skill packages. Selected instructions and references are loaded by SkillsMiddleware; uploading does not install dependencies.',
      helpTooltip: 'The catalog holds instructions, references and scripts. Scripts run in the session sandbox; dependencies come from its deployed image.',
      addSkill: 'Add skill',
      addStepRegister: 'Register',
      addFileSelected: 'Selected {name}',
      addClearFile: 'Clear',
      emptyDesc: 'No skill packages yet. Upload a ZIP or add a source.',
      deleteCatalog: 'Remove from catalog',
      deleteCatalogConfirm: 'Delete “{name}” from the catalog? Historical installation records remain; referenced entries cannot be deleted.',
      deleteSuccess: 'Removed from catalog',
      registerAccepted: 'Added to catalog',
      loadFailed: 'Failed to load'
    },
    mcpService: 'MCP Service',
    workspaceSettings: 'Workspace Settings',
    navGroups: {
      systemAdministration: 'System Administration'
    },
    roleDenied: {
      title: 'Insufficient permissions',
      desc: 'Your role can\'t access this settings page. Ask an admin of this workspace to grant the required role.'
    },
    capabilityUnavailable: 'This feature is not supported by the current deployment. You have been returned to an available page.',
    parser: {
      title: 'Parser Engine'
    },
    storage: {
      title: 'Storage Engine',
      engineLocal: 'Local',
      engineCos: 'Tencent Cloud COS',
      engineTos: 'Volcengine TOS',
      engineOss: 'Alibaba Cloud OSS'
    },
    hostApprovalDefault: {
      title: 'Default execution approval',
      description: 'When the agent deletes a file or writes outside the workspace, this chooses whether to ask you each time or let the model approve it. New chats start here; switch the current chat to the left of the input box.'
    }
  },
  envVarSettings: {
    host: {
      title: 'Environment variables'
    }
  },
  defaultSettings: {
    saving: 'Saving',
    loadFailed: 'Could not load defaults. Retry before editing.',
    title: 'Defaults',
    readOnly: 'Only workspace admins can change these. You can see which defaults are in effect.',
    webSearchGroup: 'Web search',
    slots: {
      chat: {
        label: 'Default chat model',
        description: 'Used by new agents and Q&A, and as the fallback for background tasks.',
        none: 'No chat model is available, so Q&A and background generation will not work.'
      },
      utility: {
        label: 'Lightweight generation model',
        description: 'Used for short tasks such as session titles, MCP usage instructions. A faster, cheaper model works well.',
        none: 'No chat model is available, so titles and instructions cannot be generated.'
      },
      embedding: {
        label: 'Default embedding model',
        description: 'Preselected for new knowledge bases. Existing knowledge bases are unchanged.',
        none: 'No embedding model is available, so knowledge bases cannot be created.'
      },
      rerank: {
        label: 'Default rerank model',
        description: 'Used by searches and built-in agents that have no rerank model of their own.',
        none: 'No rerank model is available, so search results keep their retrieval order.'
      },
      vlm: {
        label: 'Default vision model',
        description: 'Default choice for image understanding and multimodal parsing.',
        none: 'No vision model is available, so image understanding is unavailable.'
      },
      asr: {
        label: 'Default speech recognition model',
        description: 'Default choice for audio and video transcription.',
        none: 'No speech recognition model is available, so transcription is unavailable.'
      }
    },
    hints: {
      workspace: 'Using the workspace setting.',
      system: 'Not set. Currently using the system default: {name}',
      auto: 'Not set. Currently using the first available model: {name}',
      followChat: 'Not set. Following the default chat model: {name}',
      staleFallback: 'The selected model was deleted or is unavailable. Currently falling back to: {name}',
      staleNone: 'The selected model was deleted or is unavailable, and there is nothing to fall back to.'
    },
    webSearch: {
      label: 'Default search engine',
      description: 'Used when web search is on for an agent that has no search engine of its own.',
      unset: 'No default search engine. Agents without their own search engine cannot search the web.',
      placeholder: 'Select a search engine'
    },
    toasts: {
      saveFailed: 'Save failed: {message}'
    }
  },
  retrievalSettings: {
    title: 'Search Settings',
    description: 'Configure global retrieval parameters for knowledge search and message search; values pass through to the official ContextDB query API',
    topKLabel: 'Results per query (Top K)',
    topKDescription: 'Number of chunks returned per query, range 1-10; official ContextDB default is 5',
    similarityThresholdLabel: 'Similarity threshold',
    similarityThresholdDescription: 'Chunks below this relevance are filtered out, range 0-1; official ContextDB default is 0.6',
    vectorWeightLabel: 'Vector weight',
    vectorWeightDescription: 'Balance between vector and keyword retrieval, range 0-1; official ContextDB default is 0.7',
    queryRewriteLabel: 'Query rewrite',
    queryRewriteDescription: 'ContextDB rewrites the query with an LLM before retrieval; off by default officially, on by default here',
    toasts: {
      saveSuccess: 'Retrieval configuration saved',
      saveFailed: 'Failed to save configuration: {message}'
    }
  },
  graphSettings: {
    title: 'Knowledge Graph Configuration',
    description: 'Configure entity-relationship extraction to automatically build a knowledge graph from text (note: this is different from the "page-link graph" inside the Wiki — that one shows references between Wiki pages, while this one is an LLM-extracted entity-relationship graph)',
    enableLabel: 'Enable Entity-Relationship Extraction',
    enableDescription: 'Automatically extract entities and relationships from text when enabled',
    tagsLabel: 'Relationship Types',
    tagsDescription: 'Define relationship type tags to extract, separated by commas',
    tagsPlaceholder: 'Enter relationship types, e.g., works_at, colleague, friend',
    generateRandomTags: 'Generate Random Tags',
    sampleTextLabel: 'Sample Text',
    sampleTextDescription: 'Sample text for testing entity-relationship extraction',
    sampleTextPlaceholder: 'Enter text containing entities and relationships...',
    customInstructionsLabel: 'Additional Extraction Instructions',
    customInstructionsDescription: 'Add domain scope, entity filtering, or attribute guidance while the system retains the structured output contract',
    customInstructionsPlaceholder: 'For example: focus on contract parties, amounts, performance dates, and liabilities…',
    generateRandomText: 'Generate Random Text',
    entityListLabel: 'Entity List',
    entityListDescription: 'Entities and their attributes extracted from text',
    nodeNamePlaceholder: 'Enter entity name',
    attributePlaceholder: 'Enter attribute value',
    addAttribute: 'Add Attribute',
    manageEntitiesLabel: 'Manage Entities',
    manageEntitiesDescription: 'Add or remove entity nodes',
    addEntity: 'Add Entity',
    relationListLabel: 'Relationship List',
    relationListDescription: 'Define relationship connections between entities',
    selectEntity: 'Select Entity',
    selectRelationType: 'Select Relationship Type',
    manageRelationsLabel: 'Manage Relationships',
    manageRelationsDescription: 'Add or remove relationships between entities',
    addRelation: 'Add Relationship',
    extractActionsLabel: 'Extraction Actions',
    extractActionsDescription: 'Perform entity-relationship extraction or manage sample data',
    startExtraction: 'Start Extraction',
    extracting: 'Extracting...',
    defaultExample: 'Default Example',
    clearExample: 'Clear Example',
    completeModelConfig: 'Please complete model configuration first',
    tagsGenerated: 'Tags generated successfully',
    tagsGenerateFailed: 'Failed to generate tags',
    textGenerated: 'Text generated successfully',
    textGenerateFailed: 'Failed to generate text',
    pleaseInputText: 'Please enter sample text first',
    extractSuccess: 'Entity-relationship extraction successful',
    extractFailed: 'Entity-relationship extraction failed',
    exampleLoaded: 'Example loaded',
    exampleCleared: 'Example cleared',
    checkingAvailability: 'Checking knowledge graph availability…',
    checkAvailabilityFailed: 'Unable to check knowledge graph availability. Please retry.',
    disabledWarning: 'Knowledge graph database is not enabled, entity-relationship extraction will not be available',
    howToEnable: 'How to enable knowledge graph?'
  },
  initialization: {
    skip: 'Skip',
    next: 'Next'
  },
  inviteRegister: {
    bannerTitle: 'You have been invited to join "{tenant}"',
    bannerHint: 'Fill in the details below to register. You will join the team automatically once registration completes.',
    bannerHintLogin: 'Log in to join this team automatically.',
    loading: 'Verifying invitation link…',
    invalidTitle: 'Invitation link is invalid or revoked',
    invalidBody: 'Ask your inviter to send a new link, or sign in with an existing account.',
    backToLogin: 'Back to login',
    title: 'Complete registration',
    subtitle: 'You\'ve been invited to join “{tenant}”',
    email: 'Email',
    emailPlaceholder: 'your{\'@\'}example.com',
    emailHint: 'Use any email address you control.',
    emailInvalid: 'Please enter a valid email address',
    username: 'Display name',
    usernamePlaceholder: 'Enter your display name',
    password: 'Set a password',
    passwordPlaceholder: 'At least 6 characters',
    confirmPassword: 'Confirm password',
    submit: 'Complete registration',
    submitting: 'Submitting…',
    success: 'Registration successful — entering workspace…',
    joined: 'You have joined the team.',
    failed: 'Registration failed; please try again later',
    usernameRequired: 'Display name is required',
    passwordTooShort: 'Password must be at least 6 characters',
    passwordMismatch: 'Passwords do not match'
  },
  auth: {
    account: 'Account',
    accountPlaceholder: 'Enter account',
    accountRequired: 'Enter account',
    accountDescription: 'Your platform sign-in account',
    login: 'Login',
    logout: 'Logout',
    oidcLogin: 'Sign in with OIDC',
    oidcLoginWithProvider: 'Sign in with {provider}',
    redirectingToOIDC: 'Redirecting to identity provider...',
    orContinueWith: 'Or continue with',
    oidcLoginFailed: 'OIDC login failed',
    username: 'Username',
    email: 'Email',
    password: 'Password',
    confirmPassword: 'Confirm Password',
    loginSuccessTitle: 'Login successful',
    loginSuccessContent: 'Welcome back. You are now in {name}',
    loggingIn: 'Logging in...',
    register: 'Register',
    registering: 'Registering...',
    createAccount: 'Create Account',
    haveAccount: 'Already have an account?',
    backToLogin: 'Back to Login',
    loginHint: 'Sign in to continue, or create an account below if this is your first time.',
    firstTime: 'First time here?',
    registerSuccess: 'Registration successful. Please sign in',
    registerFailed: 'Registration failed',
    registerSubtitle: 'Create an account to get started',
    emailPlaceholder: 'Enter email address',
    passwordPlaceholder: 'Enter password',
    confirmPasswordPlaceholder: 'Enter password again',
    usernamePlaceholder: 'Enter username',
    emailRequired: 'Enter email address',
    emailInvalid: 'Enter correct email format',
    passwordRequired: 'Enter password',
    passwordMinLength: 'Password must be at least 8 characters',
    passwordMaxLength: 'Password cannot exceed 1024 characters',
    passwordMustContainLetter: 'Password must contain letters',
    passwordMustContainLowercaseLetter: 'Password must contain lowercase letters',
    passwordMustContainUppercaseLetter: 'Password must contain uppercase letters',
    passwordMustContainNumber: 'Password must contain numbers',
    passwordMustContainSpecialChar: 'Password must contain special characters: {specialChars}',
    usernameRequired: 'Enter username',
    usernameMinLength: 'Username must be at least 2 characters',
    usernameMaxLength: 'Username cannot exceed 20 characters',
    usernameInvalid: 'Username can only contain letters, numbers, underscores and Chinese characters',
    confirmPasswordRequired: 'Confirm password',
    passwordMismatch: 'Entered passwords do not match',
    loginError: 'Login error, please check account or password',
    loginErrorRetry: 'Login error, please try again later',
    registerError: 'Registration error, please try again later',
    workspaceOnboarding: {
      title: 'Choose your workspace',
      description: 'Create a personal workspace to continue.',
      create: 'Create workspace',
      invitations: 'View invitations',
      loadingPolicy: 'Checking the available workspace options…',
      policyLoadFailed: 'Workspace permissions could not be loaded. Check your connection and try again.',
      retry: 'Reload',
      inviteOnlyTitle: 'Waiting for a workspace invitation',
      inviteOnlyDescription: 'Personal workspace creation is disabled. View and accept an invitation from a workspace administrator.',
      inviteOnlyNotice: 'This account can only join an existing workspace by invitation',
      help: 'You can create a workspace now or return later to accept an invitation.',
      inviteOnlyHelp: 'No invitation yet? Send your registered email address to a workspace administrator and ask them to invite you.'
    }
  },
  authStore: {
    errors: {
      parseUserFailed: 'Failed to parse user information',
      parseTenantFailed: 'Failed to parse workspace information',
      parseKnowledgeBasesFailed: 'Failed to parse knowledge base list',
      parseCurrentKnowledgeBaseFailed: 'Failed to parse current knowledge base'
    }
  },
  common: {
    confirm: 'Confirm',
    cancel: 'Cancel',
    unsavedChanges: {
      title: 'Unsaved changes',
      body: 'Your changes will be lost if you close now. Close anyway?',
      discard: 'Discard changes',
      keepEditing: 'Keep editing'
    },
    fullscreen: 'Full screen',
    exitFullscreen: 'Exit full screen',
    save: 'Save',
    delete: 'Delete',
    edit: 'Edit',
    copy: 'Copy',
    copied: 'Copied',
    copySuccess: 'Copied successfully',
    loading: 'Loading...',
    noMoreData: 'All content loaded',
    loadMore: 'Load more',
    error: 'Error',
    success: 'Success',
    failed: 'Failed',
    selectAll: 'Select All',
    yes: 'Yes',
    no: 'No',
    close: 'Close',
    back: 'Back',
    next: 'Next',
    finish: 'Finish',
    all: 'All',
    clear: 'Clear',
    on: 'On',
    off: 'Off',
    confirmDelete: 'Confirm Delete',
    deleteFailed: 'Delete failed',
    operationFailed: 'Operation failed',
    file: 'File',
    skill: 'Skills',
    knowledgeBase: 'Knowledge Base',
    noResult: 'No results',
    remove: 'Remove',
    avatar: 'Avatar',
    defaultUser: 'User',
    copyFailed: 'Copy failed',
    retry: 'Retry',
    expand: 'Expand'
  },
  mentionBrowser: {
    browse: 'Browse by folder',
    path: 'Folder path',
    root: 'Root',
    searchFolder: 'Search this folder',
    searchKb: 'Search knowledge bases',
    subtree: 'Search includes subfolders.',
    wholeKb: 'The whole knowledge base is still selected; picking a file does not narrow that scope.',
    tags: 'Existing tags still filter the selected files.',
    folderCount: '{count} documents including subfolders',
    selected: 'Already selected',
    deleting: 'Being deleted',
    unsupported: 'Unsupported by this agent',
    forbidden: 'You no longer have access to this content.',
    missing: 'This folder is no longer available. Go back and select it again.',
    error: 'Could not load this folder. Please retry.',
    retry: 'Retry',
    empty: 'No files in this view.',
    previous: 'Previous',
    next: 'Next',
    page: 'Page {page} · {total} documents'
  },
  mentionDetail: {
    readOnlyFromAgent: 'Read-only in this conversation; not shown in Knowledge Base list',
    faqCount: '{count} Q&A entries',
    kbCount: '{count} documents',
    mcpToolCount: '{count} tools',
    mcpNotSynced: 'Tools not synced yet',
    mcpStale: 'Needs resync',
    belongsToKb: 'Knowledge base: ',
    belongsToOrg: 'Space: ',
    noCompatibleKbForAgent: 'This agent\'s tools don\'t match any knowledge base\'s capabilities in scope, so nothing can be referenced.',
    tag: 'Tags',
    searchPlaceholder: 'Search KBs, files, skills…',
    searchInGroup: 'Search in {group}…',
    typeToSearch: 'Keep typing after {\'@\'} to search…',
    viewAll: 'View all',
    back: 'Back'
  },
  file: {
    upload: 'Upload File'
  },
  manualEditor: {
    assistant: {
      button: 'Assistant',
      tooltip: 'Let the assistant help you write',
      continue: 'Continue writing',
      outline: 'Draft an outline',
      polish: 'Polish the text',
      summarize: 'Summarize',
      open: 'Open assistant',
      prompts: {
        continue: 'Continue the text from its end with one more paragraph that follows on from it.',
        outline: 'Draft a clearly structured outline for this document from its title and current text, and put it at the start of the text.',
        polish: 'Polish the text: fix typos and awkward sentences without changing the meaning, section by section.',
        summarize: 'Summarize the key points of this document in the chat. Do not change the text.'
      }
    },
    placeholders: {
      heading: 'Heading {level}',
      listItem: 'List item',
      taskItem: 'Task item',
      quote: 'Quoted text',
      code: 'Code content',
      linkText: 'Link text',
      imageAlt: 'Description',
      bold: 'Bold text',
      italic: 'Italic text',
      strike: 'Strikethrough',
      inlineCode: 'code'
    },
    table: {
      column1: 'Column 1',
      column2: 'Column 2',
      cell: 'Content'
    },
    toolbar: {
      bold: 'Bold',
      italic: 'Italic',
      strike: 'Strikethrough',
      inlineCode: 'Inline code',
      heading1: 'Heading 1',
      heading2: 'Heading 2',
      heading3: 'Heading 3',
      bulletList: 'Bullet list',
      orderedList: 'Numbered list',
      taskList: 'Task list',
      blockquote: 'Blockquote',
      codeBlock: 'Code block',
      link: 'Insert link',
      image: 'Insert image',
      table: 'Insert table',
      horizontalRule: 'Horizontal rule',
      headingGroup: 'Heading',
      insertGroup: 'Insert'
    },
    shortcuts: {
      title: 'Shortcuts',
      continueList: 'Continue the list',
      indent: 'Indent / Shift+Tab to outdent'
    },
    view: {
      edit: 'Edit',
      split: 'Split',
      preview: 'Preview',
      splitUnavailable: 'Widen the drawer or go full screen to split the view',
      groupLabel: 'Editor view'
    },
    preview: {
      empty: 'No content yet'
    },
    title: {
      edit: 'Edit Markdown Knowledge',
      create: 'Create Markdown Knowledge'
    },
    section: {
      content: 'Content'
    },
    labels: {
      currentKnowledgeBase: 'Current knowledge base'
    },
    defaultTitlePrefix: 'New Document',
    error: {
      fetchDetailFailed: 'Failed to fetch knowledge details',
      saveFailed: 'Save failed, please try again later'
    },
    warning: {
      selectKnowledgeBase: 'Please select a target knowledge base',
      enterTitle: 'Please enter a knowledge title',
      enterContent: 'Please enter knowledge content',
      contentTooShort: 'Content is too short. Please add more information before publishing'
    },
    success: {
      draftSaved: 'Draft saved',
      published: 'Knowledge published and indexing started'
    },
    form: {
      knowledgeBasePlaceholder: 'Select knowledge base',
      titleLabel: 'Knowledge title',
      knowledgeBaseLabel: 'Target knowledge base',
      titlePlaceholder: 'Enter title',
      contentPlaceholder: 'Supports Markdown. Use # headings, lists, code blocks, etc.'
    },
    noDocumentKnowledgeBases: 'No document-type knowledge bases available. Please create one first',
    status: {
      draftTag: 'Status: Draft',
      publishedTag: 'Status: Published',
      lastUpdated: 'Last updated: {time}',
      counter: '{chars} characters · {lines} lines'
    },
    loading: {
      content: 'Loading content...',
      preparing: 'Preparing editor...'
    },
    actions: {
      cancel: 'Cancel',
      saveDraft: 'Save Draft',
      publish: 'Publish'
    }
  },
  input: {
    addModel: 'Add Model',
    placeholder: 'Ask a question or describe a task…',
    agentMode: 'Smart Reasoning',
    normalMode: 'Quick Answer',
    normalModeDesc: 'Knowledge base RAG Q&A',
    agentModeDesc: 'Multi-step thinking, deep analysis',
    agentMissingAllowedTools: 'Allowed tools',
    agentMissingSummaryModel: 'Chat model',
    agentMissingRerankModel: 'Rerank model',
    customAgentMissingSummaryModel: 'Chat model',
    customAgentMissingRerankModel: 'Rerank model',
    goToAgentEditor: 'Go to configure →',
    agentNotReadyDetail: 'Agent "{agentName}" is not ready. Please configure: {reasons}',
    sharedAgentNotReadyDetail: 'Shared agent "{agentName}" is not ready (missing: {reasons}). Ask the sharing organization admin to finish setup.',
    webSearch: {
      toggleOn: 'Enable Web Search',
      toggleOff: 'Disable Web Search',
      notConfigured: 'Web search engine not configured'
    },
    knowledgeBase: 'Knowledge Base',
    knowledgeBaseWithCount: 'Knowledge Base ({count})',
    notConfigured: 'Not configured',
    sharedAgentModelLabel: 'Model from shared agent',
    noModel: 'No available models',
    modelAuto: 'Default',
    modelFollowDefault: 'Follow default',
    modelAutoHint: 'The current knowledge base\'s chat model, or the first available chat model outside a knowledge base or when it has none',
    stopGeneration: 'Stop Generation',
    send: 'Send',
    steerRetry: 'Retry sending',
    messages: {
      enterContent: 'Please enter content first!',
      replying: 'Currently replying, please try again later!',
      steerFailed: 'Failed to append the message. Please try again.',
      agentSwitchedOn: 'Switched to Intelligent Reasoning',
      agentSwitchedOff: 'Switched to Quick Q&A',
      agentSelected: 'Selected agent "{name}"',
      webSearchNotConfigured: 'Web search engine is not configured. Please configure a provider and credentials in settings.',
      webSearchEnabled: 'Web search enabled',
      webSearchDisabled: 'Web search disabled',
      sessionMissing: 'Session ID does not exist',
      messageMissing: 'Unable to get message ID. Please refresh the page and try again.',
      stopSuccess: 'Generation stopped',
      stopFailed: 'Failed to stop. Please try again.'
    },
    webSearchDisabledByAgent: 'Web search is disabled by the current agent',
    kbLockedByAgent: 'Knowledge base configuration is locked by the current agent',
    kbDisabledByAgent: 'Knowledge base is disabled by the current agent',
    modelLockedByAgent: 'Model selection is locked by the current agent',
    imageUploadDisabledByAgent: 'Image upload is not enabled for this agent',
    voiceTooltip: 'Hold to talk ({shortcut})',
    voicePreparing: 'Opening microphone, start talking when the button turns red',
    voiceRecording: 'Recording, release to finish',
    voiceReleasedEarly: 'The microphone was not ready yet. Hold until the button turns red, then talk.',
    voiceTranscribing: 'Transcribing…',
    voiceUnsupported: 'This browser does not support audio recording',
    voiceInsecureContext: 'Voice input requires HTTPS or localhost',
    voicePermissionDenied: 'Microphone access was denied. Allow it in your browser settings.',
    voiceDeviceError: 'No microphone available',
    voiceDecodeError: 'Could not process the recording. Please try again.',
    voiceTranscribeFailed: 'Transcription failed. Check the agent\'s ASR model settings.',
    voiceEmptyResult: 'No speech detected',
    goToAgentSettings: 'Go to agent settings',
    hostApprovalMode: {
      ask: 'Ask me',
      askHint: 'Asks you before deletes and writes outside the workspace',
      auto: 'Approve for me',
      autoHint: 'A model decides for you without interrupting',
      switchFailed: 'Could not switch the approval mode'
    }
  },
  createChat: {
    title: 'Hi, I am Xiaozhi — your knowledge, within reach',
    newSessionTitle: 'New Session',
    openProject: 'Select project',
    clearProject: 'Clear',
    pickFailed: 'Could not open the selected path',
    messages: {
      createFailed: 'Failed to create session',
      createError: 'Failed to create session, please try again later'
    }
  },
  knowledgeList: {
    empty: {
      title: 'No knowledge bases yet'
    },
    sections: {
      tenantOthers: 'Workspace · Other members',
      tenantReadonly: 'Workspace · View only'
    },
    detail: {
      title: 'Shared Knowledge Base',
      sourceOrg: 'Space',
      myPermission: 'My Permission'
    }
  },
  embedPublish: {
    copyCode: 'Copy code'
  },
  knowledgeEditor: {
    activity: {
      title: 'Activity',
      description: 'Important changes and background-task entry points for this knowledge base. Retention follows the audit-log policy.',
      allOutcomes: 'All outcomes',
      allActions: 'All actions',
      refresh: 'Refresh',
      retry: 'Retry',
      empty: 'No activity yet',
      emptyFiltered: 'No matching activity records',
      clearFilters: 'Clear filters',
      loadingMore: 'Loading…',
      end: 'No earlier activity',
      loadFailed: 'Failed to load activity',
      columns: {
        time: 'Time',
        action: 'Action',
        target: 'Target',
        actor: 'Initiator',
        outcome: 'Outcome'
      },
      expanded: {
        targetType: 'Target type',
        targetId: 'Target ID',
        actorId: 'Initiator ID',
        apiKeyName: 'API key name',
        apiKeyId: 'API key ID',
        agentSessionId: 'Assistant conversation ID',
        agentOperation: 'Assistant operation',
        details: 'Details'
      },
      drawer: {
        sectionSummary: 'Summary',
        sectionIdentifiers: 'Identifiers',
        sectionTask: 'Task information',
        targetChange: 'Change details'
      },
      systemActor: 'System',
      actorWithAPIKey: '{actor} · API Key · {name}',
      actorAPIKey: 'API Key · {name}',
      viaAssistant: 'Via Xiaozhi Assistant',
      knowledgeBase: 'Knowledge base',
      countItems: '{count} items',
      titleWithCount: '{title} and {count} more',
      importSummary: 'Success {success} / Failed {failed} / Skipped {skipped}',
      targets: {
        knowledge_base: 'Knowledge base',
        knowledge: 'Knowledge',
        faq_entry: 'FAQ entry',
        knowledge_tag: 'Tag',
        data_source: 'Data source',
        knowledge_base_share: 'Share',
        knowledge_move: 'Knowledge move',
        wiki: 'Wiki'
      },
      detailFields: {
        task_id: 'Task ID',
        trigger: 'Trigger',
        processing_status: 'Processing status',
        source_kb_id: 'Source knowledge base ID',
        target_kb_id: 'Target knowledge base ID',
        sync_log_id: 'Sync log ID',
        mode: 'Mode',
        attempt: 'Processing attempt',
        count: 'Item count',
        total: 'Total',
        processed: 'Processed',
        failed: 'Failed',
        skipped: 'Skipped',
        failure_stage: 'Failure stage'
      },
      actions: {
        'kb.created': 'Knowledge base created',
        'kb.updated': 'Knowledge base updated',
        'kb.deleted': 'Knowledge base deleted',
        'kb.duplicated': 'Knowledge base duplicated',
        'kb.clone_started': 'Clone started',
        'kb.clone_completed': 'Clone completed',
        'kb.clone_failed': 'Clone failed',
        'knowledge.created': 'Knowledge added',
        'knowledge.updated': 'Knowledge updated',
        'knowledge.deleted': 'Knowledge deleted',
        'knowledge.batch_deleted': 'Knowledge batch deleted',
        'knowledge.reparse_started': 'Reparse started',
        'knowledge.parse_canceled': 'Parsing canceled',
        'knowledge.move_started': 'Knowledge move started',
        'knowledge.move_completed': 'Knowledge move completed',
        'knowledge.move_failed': 'Knowledge move failed',
        'tag.created': 'Tag created',
        'tag.updated': 'Tag updated',
        'tag.deleted': 'Tag deleted',
        'datasource.created': 'Data source created',
        'datasource.updated': 'Data source updated',
        'datasource.deleted': 'Data source deleted',
        'datasource.sync_started': 'Data source sync started',
        'datasource.sync_completed': 'Data source sync completed',
        'datasource.sync_failed': 'Data source sync failed',
        'datasource.paused': 'Data source paused',
        'datasource.resumed': 'Data source resumed',
        'kb.share_added': 'Share added',
        'kb.share_permission_changed': 'Share permission changed',
        'kb.share_removed': 'Share removed',
        'wiki.content_changed': 'Wiki content changed',
        'faq.import_started': 'FAQ import started',
        'faq.import_completed': 'FAQ import completed',
        'faq.import_failed': 'FAQ import failed'
      },
      outcomes: {
        accepted: 'Accepted',
        success: 'Success',
        failed: 'Failed',
        partial: 'Partial',
        canceled: 'Canceled',
        denied: 'Denied'
      },
      detailValues: {
        user: 'User initiated',
        manual: 'Manual',
        schedule: 'Scheduled',
        system: 'System',
        pending: 'Pending',
        completed: 'Completed',
        partial: 'Partially completed',
        canceled: 'Canceled',
        failed: 'Failed',
        enqueue: 'Task submission',
        reuse_vectors: 'Reuse vectors',
        reparse: 'Reparse',
        viewer: 'Read-only',
        editor: 'Can edit',
        admin: 'Manage',
        append: 'Append',
        replace: 'Replace'
      }
    },
    titleCreate: 'Create Knowledge Base',
    titleEdit: 'Knowledge Base Settings',
    navGroups: {
      basic: 'Basics',
      processing: 'Indexing & Parsing',
      data: 'Storage & Data',
      integration: 'Publishing',
      management: 'Management & Audit'
    },
    sidebar: {
      basic: 'Basic Information',
      models: 'Model Configuration',
      vectorStore: 'Vector Store',
      chunking: 'Chunking Settings',
      storage: 'Storage Engine',
      advanced: 'Advanced Settings',
      faq: 'FAQ Settings',
      graph: 'Knowledge Graph',
      multimodal: 'Image Processing',
      asr: 'Audio',
      datasource: 'Data Sources',
      share: 'Sharing',
      activity: 'Activity'
    },
    errors: {
      vectorStoreBindingInvalid: 'The selected vector store cannot be used. Choose a different store or use the system default.',
      vectorStoreUnavailable: 'The selected vector store is currently unavailable. Check its connection configuration in Settings → Vector Stores.'
    },
    basic: {
      title: 'Basic Information',
      description: 'Configure the knowledge base name and description',
      kbId: 'Knowledge Base ID',
      kbIdDesc: 'Use this ID to target the knowledge base in API integrations',
      typeLabel: 'Knowledge Base Type',
      typeDocument: 'Document-based',
      typeFAQ: 'FAQ Q&A',
      typeDescription: 'FAQ suits structured Q&A datasets; document type supports file parsing and chunking; Wiki type auto-builds interlinked knowledge pages via LLM.',
      nameLabel: 'Knowledge Base Name',
      namePlaceholder: 'Enter knowledge base name',
      descriptionLabel: 'Knowledge Base Description',
      descriptionPlaceholder: 'Enter knowledge base description (optional)',
      profile: {
        title: 'AI-generated description',
        hint: 'Derived from the document profiles. It never overwrites the manual description above; agents read both to decide whether a question belongs to this knowledge base.',
        empty: 'Not generated yet. Upload documents, let their summaries finish, then use the button below.',
        noDocuments: 'No parsed documents in this knowledge base yet.',
        questions: 'Typical questions',
        generate: 'Generate AI description',
        regenerate: 'Regenerate',
        adopt: 'Use as description',
        generated: 'AI description generated',
        generateFailed: 'Failed to generate the AI description',
        adopted: 'Copied into the description; save to apply',
        failed: 'Last generation failed: {error}',
        generatedAt: 'Generated {time} · based on {count} documents'
      }
    },
    wiki: {
      title: 'Wiki Settings',
      synthesisModelLabel: 'Wiki Synthesis Model',
      synthesisModelPlaceholder: 'Select the LLM model for Wiki generation',
      synthesisModelTip: 'Falls back to the summary model if not set',
      autoGenerateLabel: 'Automatically generate Wiki pages',
      autoGenerateTip: 'When disabled, Wiki pages remain available for browsing and manual editing, but document processing will not call the LLM to generate or update pages',
      extractionGranularityLabel: 'Extraction Granularity',
      contentInstructionsLabel: 'Wiki Content Instructions',
      contentInstructionsTip: 'Control emphasis and tone for summaries, pages, and the index. Citation, merge, and factuality rules remain system-owned. Reprocess existing content to apply changes.',
      contentInstructionsPlaceholder: 'For example: use a legal-review tone and emphasize owners, timelines, and risks…',
      extractionInstructionsLabel: 'Wiki Extraction Focus',
      extractionInstructionsTip: 'Describe domain entities and concepts to prioritize without replacing the system JSON and citation protocol.',
      extractionInstructionsPlaceholder: 'For example: prioritize products, versions, organizations, owners, and core technical concepts…',
      extractionGranularityTip: 'Controls how many Wiki entities/concepts are extracted per document. Finer = tighter index, coarser = more comprehensive',
      granularityFocused: 'Focused',
      granularityStandard: 'Standard',
      granularityExhaustive: 'Exhaustive',
      granularityFocusedHint: 'Extract only the document’s main subjects (e.g. a resume yields the person and their projects). Cleanest, may miss secondary entities.',
      granularityStandardHint: 'Main subjects plus secondary entities/concepts that receive substantial discussion. Skips name-dropped terms. Recommended default.',
      granularityExhaustiveHint: 'Extract every named entity and concept, including passing mentions of stacks/tools. Use when the KB serves as a glossary.'
    },
    indexing: {
      title: 'Indexing Strategy',
      description: 'Configure document processing pipelines. Each indexing method can be enabled or disabled independently.',
      searchTitle: 'RAG Search',
      searchDesc: 'Chunk, vectorize and keyword-index documents for hybrid retrieval',
      wikiTitle: 'Wiki Knowledge Base',
      wikiDesc: 'Auto-generate interlinked wiki pages to build a structured knowledge system',
      atLeastOne: 'At least one indexing strategy must be enabled',
      embeddingRequired: 'RAG search requires an Embedding model',
      lockedTip: 'The indexing strategy cannot be changed once the knowledge base contains content. Please clear the knowledge base first.',
      rebuildConfirmTitle: 'Rebuild Index',
      rebuildConfirmBody: 'Indexing strategy has changed. Re-process {count} existing documents? This may take some time.',
      rebuildSuccess: 'Rebuild task submitted for {count} documents',
      rebuildSkip: 'You can manually trigger a rebuild later from Data Sources'
    },
    wikiBrowser: {
      viewInGraph: 'View in Graph',
      gallery: {
        attr: {
          builtin_caption: 'Caption',
          builtin_caption_description: 'The model-generated description of the image.',
          builtin_ocr_text: 'OCR text',
          builtin_ocr_text_description: 'Text extracted from the image by OCR.',
          builtin_page: 'Document page',
          builtin_page_description: 'Group by source document, then sort by PDF page; unknown pages come last within each document.',
          builtin_created_at: 'Created time',
          builtin_created_at_description: 'When the owning document chunk was created.',
          builtin_updated_at: 'Updated time',
          builtin_updated_at_description: 'When the owning document chunk was last updated.',
          builtin_is_enabled: 'Enabled',
          builtin_is_enabled_description: 'Whether the owning document chunk takes part in retrieval.',
          builtin_is_enabled_value_true: 'Enabled',
          builtin_is_enabled_value_false: 'Disabled'
        }
      },
      filterSummary: 'Summaries',
      filterEntity: 'Entities',
      filterConcept: 'Concepts',
      filterSynthesis: 'Synthesis',
      filterComparison: 'Comparisons',
      version: 'v{ver}'
    },
    buttons: {
      create: 'Create Knowledge Base',
      saveAndClose: 'Save and Close'
    },
    footer: {
      instantEffect: 'Changes on this page take effect immediately; no save needed'
    },
    postCreateHint: {
      title: 'Created successfully',
      footer: 'Keep adjusting settings, configure sharing and data sources, then click "Save and Close".',
      followUpDesc: 'Configure data sources on the left, or use Share Management to publish to spaces'
    },
    share: {
      description: 'Share the knowledge base with spaces so members can access and use it',
      hintTitle: 'Sharing notes',
      addShare: 'Share',
      unshareConfirm: 'Are you sure you want to unshare from "{name}"?',
      tip1: 'After sharing, space members will access this knowledge base based on the assigned permissions',
      tip2: 'Editable permission allows members to modify content; Read-only permission only allows retrieval and Q&A'
    },
    messages: {
      loadModelsFailed: 'Failed to load model list',
      loadDataFailed: 'Failed to load knowledge base data',
      notFound: 'Knowledge base not found',
      nameRequired: 'Please enter the knowledge base name',
      summaryRequired: 'Please select a summary model',
      multimodalInvalid: 'Multimodal configuration validation failed',
      createSuccess: 'Knowledge base created successfully',
      createFailed: 'Failed to create knowledge base',
      missingId: 'Knowledge base ID is missing',
      buildDataFailed: 'Failed to construct submission data',
      updateSuccess: 'Configuration saved successfully',
      indexModeRequired: 'Please select an indexing mode for FAQ knowledge bases',
      storageChangeConfirm: 'This knowledge base already has files. Changing the storage engine may make old files inaccessible. Do you want to proceed?'
    },
    document: {
      title: 'Document Management'
    },
    faq: {
      title: 'FAQ Configuration',
      description: 'Configure indexing strategy and guidance for FAQ-style knowledge bases',
      indexModeLabel: 'Indexing Mode',
      indexModeDescription: 'Question-only indexing improves precision, question+answer improves recall.',
      questionIndexModeLabel: 'Question Indexing Mode',
      questionIndexModeDescription: 'Combined: Standard and similar questions are indexed together. Separate: Each question is indexed independently for more precise retrieval but requires more storage.',
      entryGuide: 'Each FAQ entry contains a primary question, similar questions, negative examples, and multiple answers. Manage them in the FAQ knowledge base detail view.',
      modes: {
        questionOnly: 'Questions only',
        questionAnswer: 'Question + answer',
        combined: 'Combined',
        separate: 'Separate'
      }
    },
    faqImport: {
      title: 'Batch Import FAQ'
    },
    models: {
      title: 'Model Configuration',
      description: 'Select appropriate AI models for the knowledge base',
      llmLabel: 'LLM Model',
      llmDesc: 'Large language model used for summarization and abstract generation (optional)',
      llmPlaceholder: 'Select an LLM model (optional)',
      embeddingLabel: 'Embedding Model',
      embeddingDesc: 'Embedding model used for text vectorization',
      embeddingPlaceholder: 'Select an embedding model',
      embeddingLocked: 'Knowledge base already has files. Embedding model cannot be modified',
      embeddingOptional: '(Optional)',
      embeddingWikiOptionalDesc: 'Optional. When set, it powers similarity matching for Wiki directory classification so new pages reuse existing folders better; otherwise the full directory tree is used.'
    },
    chunking: {
      title: 'Chunking Settings',
      description: 'Controls how uploaded documents are split before embedding. Defaults work for most cases — tune only when retrieval quality is off.',
      sizeLabel: 'Chunk Size',
      sizeDescription: 'Maximum characters per chunk (100–4000). Default 512 ≈ 100–130 English tokens. Smaller for FAQs (200–400), larger for narrative documents (1000–2000).',
      characters: 'characters',
      overlapLabel: 'Chunk Overlap',
      overlapDescription: 'Characters shared between adjacent chunks (0–500). Default 80 ≈ 15% of size — sweet spot per current research. Use 0 for FAQs/structured data, 150–200 for long-form narratives.',
      separatorsLabel: 'Separators',
      separatorsDescription: 'Characters or strings the splitter prefers when cutting. Higher-priority separators are tried first; the default order favors paragraph → sentence → punctuation breaks.',
      separatorsPlaceholder: 'Select or customize separators',
      separators: {
        doubleNewline: 'Double newline ()',
        singleNewline: 'Single newline ()',
        periodCn: 'Chinese period (。)',
        exclamationCn: 'Exclamation mark (！)',
        questionCn: 'Question mark (？)',
        semicolonCn: 'Chinese semicolon (；)',
        semicolonEn: 'Semicolon (;)',
        space: 'Space ( )'
      },
      parentChildLabel: 'Parent-Child Chunking',
      parentChildDescription: 'Two-level chunking: small child chunks are vector-matched (precise hits) but the larger parent chunk is returned to the LLM (richer context). Recommended for long documents (>10 pages); skip for short FAQs to save storage.',
      parentChunkSizeLabel: 'Parent Chunk Size',
      parentChunkSizeDescription: 'Size of the context chunk returned to the LLM (512–8192). Default 4096 ≈ 1000 English tokens, fits comfortably in any modern LLM context window.',
      childChunkSizeLabel: 'Child Chunk Size',
      childChunkSizeDescription: 'Size of the embedded chunk used for vector match (64–2048). Default 384 ≈ 80 tokens — sweet spot for sentence-transformer / BGE-style embedders.',
      strategyLabel: 'Chunking Strategy',
      strategyDescription: 'Choose how documents are split into chunks. The Automatic mode profiles each document and picks the best strategy.',
      strategyPlaceholder: 'Select a chunking strategy (splits by length if left empty)',
      strategies: {
        auto: {
          label: 'Automatic',
          tooltip: 'A document profiler picks between heading-aware, structure-aware and length-based splitting per upload.'
        },
        heading: {
          label: 'Heading-aware',
          tooltip: 'Splits at Markdown heading boundaries (#, ##, ###); each chunk carries its heading path. Best for well-structured Markdown.'
        },
        heuristic: {
          label: 'Structure-aware',
          tooltip: 'Splits on detected structural cues: page-breaks, numbered sections, multilingual chapter markers (DE/EN/ZH), all-caps titles. Ideal for PDFs without Markdown headings.'
        },
        legacy: {
          label: 'Length-based',
          tooltip: 'Ignores structure; splits recursively by character count and separators — the original behavior. Use when the structure-aware strategies misbehave on your content.'
        }
      },
      overlapWarning: 'Overlap is large compared to chunk size — chunks will share most of their content.',
      advancedLabel: 'Advanced options',
      tokenLimitLabel: 'Token limit per chunk',
      tokenLimitDescription: 'Hard token cap per chunk (0–8192). 0 = off (chunk size in characters only). Activate when your embedding model has a small token limit: 200 for MiniLM (256 tok), 400 for BGE/Cohere (512 tok). Modern embedders (OpenAI, Voyage, Jina-v3) accept >2000 tokens — leave at 0.',
      languagesLabel: 'Language hints',
      languagesDescription: 'Restricts heuristic patterns to the chosen languages (DE/EN/ZH). Empty = auto-detect from sample. Set explicitly for homogeneous corpora to avoid false-positive matches across languages.',
      languagesPlaceholder: 'Auto-detect',
      languageOptions: {
        de: 'German',
        en: 'English',
        zh: 'Chinese'
      },
      debug: {
        toggle: 'Preview chunking',
        toggleHint: 'Run the chunker against sample text without re-uploading',
        sampleLabel: 'Sample text',
        samplePlaceholder: 'Paste a Markdown / plain-text snippet to see how the current configuration would chunk it…',
        presetLabel: 'Load sample:',
        samples: {
          markdown: 'Markdown doc',
          faq: 'FAQ list',
          chapter: 'PDF chapters',
          plain: 'Plain prose'
        },
        runButton: 'Run preview',
        loading: 'Running chunker on sample…',
        errorPrefix: 'Preview failed',
        selectedTier: 'Selected strategy',
        rejected: 'Rejected tiers',
        contextHeader: 'Context header',
        fallbackWarning: 'Strategy chain fell through — content does not split intelligently with current settings',
        profile: {
          lines: 'lines',
          chars: 'chars',
          headings: 'Markdown headings',
          pageBreaks: 'page breaks',
          chapterMarkers: 'chapter markers',
          languages: 'languages'
        },
        stats: {
          chunks: 'chunks',
          truncated: 'truncated; total {total}'
        }
      }
    },
    multimodal: {
      title: 'Image Processing Configuration',
      description: 'Configure image content understanding for parsing and retrieving non-text content like images'
    },
    asr: {
      title: 'Audio Speech Recognition',
      description: 'Configure ASR (speech-to-text). When enabled, you can upload audio files and transcribe them to text (e.g. mp3, wav, m4a, flac, ogg). Video upload is not supported.',
      label: 'Enable audio speech recognition',
      desc: 'When enabled, audio can be uploaded to the knowledge base; speech is transcribed to text for parsing and retrieval.',
      modelLabel: 'ASR Model',
      modelDescription: 'Speech-to-text model for audio (e.g. OpenAI Whisper)',
      modelPlaceholder: 'Select an ASR model',
      languageLabel: 'Audio language hint',
      languageDescription: 'Optional. A primary language hint can improve some ASR models; leave empty for auto-detection.',
      languagePlaceholder: 'For example zh or en; empty means auto-detect'
    },
    advanced: {
      title: 'Advanced Settings',
      description: 'Configure question generation and other advanced features',
      questionGeneration: {
        modelLabel: 'Question Generation Model',
        modelDescription: 'Leave empty to use the knowledge-base summary model.',
        modelPlaceholder: 'Select a question generation model',
        label: 'AI Question Generation',
        description: 'Generate related questions for each chunk using LLM during document parsing to improve retrieval recall. Enabling this will increase document parsing time.',
        countLabel: 'Question Count',
        countDescription: 'Number of questions to generate per document chunk (1-10)',
        instructionsLabel: 'Question Generation Instructions',
        instructionsDescription: 'Specify audience, scenario, and wording while the system retains the stable output format',
        instructionsPlaceholder: 'For example: generate natural customer-support questions and avoid exam-style wording…'
      },
      profile: {
        label: 'Auto-generate knowledge base description',
        description: 'After documents are added, removed or re-summarized, derive the description from the aggregated document profiles. The aggregation itself makes no model call; one small call runs only when the aggregate changed.',
        modelLabel: 'Generation model',
        modelDescription: 'Leave empty to reuse the knowledge-base summary model.',
        modelPlaceholder: 'Select a generation model',
        instructionsLabel: 'Description instructions',
        instructionsDescription: 'Name the audience, terms to keep or the tone; the output format stays fixed.',
        instructionsPlaceholder: 'e.g. Written for support agents; describe product lines in plain words and keep model numbers…'
      },
      autoTag: {
        label: 'Automatic Tagging',
        description: 'After parsing, select suitable tags from the existing knowledge-base tags. Tags are never created or deleted, but one extra model call is required.',
        modelLabel: 'Classification Model',
        modelDescription: 'Leave empty to reuse the knowledge-base summary model.',
        modelPlaceholder: 'Select a classification model',
        maxTagsLabel: 'Maximum tags per document',
        maxTagsDescription: 'Automatically associate 1-10 existing tags per document.',
        skipIfTaggedLabel: 'Skip documents that already have tags',
        skipIfTaggedDescription: 'When enabled, documents tagged manually at upload time are left untouched, so a deliberate classification is not diluted.'
      },
      tableMetadataInstructions: {
        label: 'Table Metadata Instructions',
        description: 'Add business context and field semantics to CSV/Excel summaries for better retrieval',
        placeholder: 'For example: this is a sales-order table, amounts are in CNY, and status uses internal codes…'
      },
      multimodal: {
        label: 'Multimodal Feature',
        description: 'Enable understanding of multimodal content such as images',
        vllmLabel: 'VLLM Vision Model',
        vllmDescription: 'Vision-language model required for multimodal understanding',
        vllmPlaceholder: 'Select a VLLM model (required)',
        descriptionLanguageLabel: 'Image Description Language',
        descriptionLanguageDescription: 'Leave empty to follow the document language instead of forcing Chinese',
        descriptionLanguageAuto: 'Follow document language',
        customInstructionsLabel: 'Image Processing Instructions',
        customInstructionsDescription: 'Add visual priorities while OCR and Markdown output contracts remain fixed',
        customInstructionsPlaceholder: 'For example: prioritize nameplates, model numbers, alarm codes, and table units…',
        imageVectorLabel: 'Image vector search',
        imageVectorDescription: 'When on, each image is also encoded by the embedding model itself after its description is generated, so searches can find images by what they show even where the description leaves it out. Needs an embedding model that takes images; costs one extra embedding call per image and widens the vector search pool. Applies to documents ingested or re-parsed afterwards; scanned PDF pages are skipped',
        imageVectorModelUnsupported: 'The current embedding model does not declare image input, so no image vectors will be indexed or recalled',
        imageAttrsSchemaLabel: 'Observable image attributes',
        imageAttrsSchemaDescription: 'The model observes the attributes below (defined by the backend registry) to drive the OCR policy',
        imagePipelineSectionLabel: 'Image parsing scheme',
        imagePipelineSectionDescription: 'With multimodal parsing on, pick how images are parsed.',
        imagePipelineLabel: 'Scheme',
        advancedSettingsLabel: 'Advanced settings',
        notesLabel: 'Additional notes',
        imagePipelinePlaceholder: 'Select a scheme',
        imagePipelineLoading: 'Loading pipelines…',
        imagePipelineLoadError: 'Could not load pipelines',
        imagePipelineValidateError: 'The current settings could not be checked; the backend re-checks them on save.',
        imageAttrsOcrConditions: 'Trigger OCR based on the observed attribute conditions',
        imageAttrsOcrConditionsDesc: 'When the observed attributes match the conditions below, OCR runs on the image',
        imagePipelineKbNote: 'Defaults follow the knowledge base settings; adjust them for this task'
      }
    }
  },
  chat: {
    suggestedQuestions: 'You can ask me',
    refreshSuggestedQuestions: 'More',
    replaceDraftTitle: 'Replace draft?',
    replaceDraftBody: 'Use this suggested question in place of the text in the message box.',
    historyLoadFailed: 'Could not load the conversation history.',
    scrollToLatest: 'Jump to latest message',
    thinking: 'Thinking...',
    thinkingAlt: 'Thinking in progress',
    conversationTime: {
      today: 'Today {time}',
      yesterday: 'Yesterday {time}',
      thisYear: '{month}/{day} {time}',
      otherYear: '{month}/{day}/{year} {time}'
    },
    preparingAnswer: 'Preparing an answer…',
    connectingModelAndGeneratingAnswer: 'Connecting to the model and generating an answer…',
    modelStillResponding: 'The model is taking longer than usual, still waiting…',
    deepThoughtCompleted: 'Deep thinking completed',
    deepThoughtAlt: 'Deep thinking finished',
    referencesTitle: 'Referenced {count} related item(s)',
    referencesDocCount: 'Referenced {count} document(s)',
    referencesWebCount: 'Referenced {count} web result(s)',
    referencesDocAndWebCount: 'Referenced {docCount} document(s) and {webCount} web page(s)',
    referencesDrawerTitle: 'Sources',
    referencesDrawerTitleWeb: 'Web sources',
    referencesDrawerTitleDocs: 'Document sources',
    referencesDrawerTitleTools: 'Tool results',
    referencesDrawerTitleMixed: 'Sources',
    referencesDrawerWebSection: 'Web',
    referencesDrawerDocsSection: 'Documents',
    referencesDrawerToolsSection: 'Tools',
    referencesDrawerEmpty: 'No sources available',
    sandbox: {
      panelTitle: 'Sandbox',
      tabArtifacts: 'Files',
      tabTerminal: 'Terminal',
      tabDesktop: 'Desktop',
      artifactsEmpty: 'No generated files in this conversation yet.',
      artifactScope: 'File scope',
      artifactsCurrent: 'This turn',
      artifactsAll: 'All files',
      artifactsSearch: 'Search filenames',
      artifactsNoMatches: 'No matching files',
      desktopNotStarted: 'The desktop is not connected yet. Connecting it attaches to this conversation\'s sandbox.',
      desktopStart: 'Connect desktop',
      desktopStarting: 'Connecting to the desktop… (3-8 seconds on first use)',
      desktopUnsupported: 'This sandbox config has no desktop. Pick a desktop-image template in the workspace sandbox settings, on a Cube or E2B backend.',
      desktopBusy: 'This conversation already has a desktop open. Only one connection is allowed at a time, otherwise two people share one keyboard and mouse.',
      desktopStartFailed: 'The desktop failed to start. You can retry.',
      desktopRebuilt: 'The sandbox was rebuilt for a skill update, so the previous desktop and any unsaved work are gone. Reconnecting gives you a fresh desktop.',
      desktopNeedsProvision: 'This conversation has no running sandbox. Create and connect starts a new sandbox, billed according to your workspace configuration.',
      desktopCreateAndStart: 'Create and connect',
      desktopPaused: 'This conversation\'s sandbox is paused. Connecting the desktop resumes it.',
      desktopDisconnected: 'Desktop disconnected',
      desktopIdleDisconnected: 'The desktop disconnected after being idle. The sandbox will pause on its own TTL. You can reconnect.',
      desktopRetry: 'Reconnect',
      paused: 'This conversation\'s sandbox is paused. Starting the terminal resumes it.',
      stopped: 'This conversation\'s sandbox is not running: it was stopped, or reclaimed after being idle. Starting the terminal restarts it; if it was reclaimed, a new sandbox is created and previous files and installed software are not kept.',
      start: 'Start terminal',
      connecting: 'Connecting to sandbox…',
      needsProvision: 'This conversation has no running sandbox. Creating one starts a new sandbox, billed according to your workspace configuration.',
      createAndStart: 'Create and start',
      noSandbox: 'No sandbox yet, and the current agent has no sandbox backend configured, so there is nowhere to create one. Switch to an agent with a sandbox configured, or send a message that runs code.',
      unsupported: 'The current sandbox backend does not support interactive terminals',
      disconnected: 'Connection lost',
      retry: 'Reconnect',
      sessionEnded: 'Terminal session ended',
      idleDisconnected: 'The terminal disconnected after being idle. The sandbox will pause on its own TTL. You can reconnect.',
      idleDisconnectedNewShell: 'The terminal disconnected after being idle and its shell has ended (background jobs started with nohup keep running). Reconnecting opens a new shell.',
      disconnectedNewShell: 'Connection lost and the terminal\'s shell has ended (background jobs started with nohup keep running). Reconnecting opens a new shell.',
      authRevoked: 'Your session is no longer valid, so the terminal was disconnected. Sign in again, then reconnect.'
    },
    questionMinimapTitle: 'Q&A',
    questionMinimapPosition: 'Turn {current} of {total}',
    questionMinimapAriaLabel: 'Question outline',
    questionMinimapAttachmentPlaceholder: '(Attachment)',
    referenceChunkCount: '{count} chunk(s)',
    fallbackHint: 'No relevant content found in knowledge base. Above is a direct response from the model.',
    truncatedHint: 'This answer was cut off at the per-response output limit. Above is what the model produced before the cut.',
    rewind: {
      tooltip: 'Rewind to here',
      confirmTitle: 'Rewind to here?',
      confirmBody: 'Later messages will be deleted. Rewinding from a question also removes that question and puts it back in the input. The workspace rolls back when a checkpoint is available. This cannot be undone.',
      confirmButton: 'Rewind',
      cancelButton: 'Cancel',
      success: 'Rewound',
      reloadFailed: 'Conversation was rewound, but history could not be reloaded. Refresh if older messages are missing',
      failed: 'Rewind failed. Please try again',
      skipped: 'Conversation rewound; workspace was left unchanged',
      skipNoSandbox: 'Conversation rewound; workspace was left unchanged (no sandbox is bound)',
      skipNoCheckpoint: 'Conversation rewound; workspace was left unchanged (no checkpoint to restore)'
    },
    requestInfoTitle: 'Request info',
    requestInfoRequestId: 'Request ID',
    requestInfoMessageId: 'Message ID',
    requestInfoSessionId: 'Session ID',
    requestInfoUrl: 'Request',
    requestInfoSentAt: 'Sent at',
    requestInfoEmpty: 'No request info available',
    channelWeb: 'Web',
    channelApi: 'API',
    channelIm: 'IM',
    chunkLabel: 'Chunk {index}:',
    navigateToDocument: 'View document details',
    referenceSourceBack: 'All sources',
    referenceSourceView: 'View in original',
    referenceSourceRelocate: 'Locate again',
    referenceSourceLocating: 'Locating the cited passage…',
    referenceSourceExact: 'Located the source passage',
    referenceSourcePartial: 'Verified source passages highlighted; part of the citation remains unmatched',
    referenceSourceBlock: 'Located the source region; exact text not confirmed',
    referenceSourceAmbiguous: 'Multiple matching passages; the location is ambiguous',
    referenceSourceStale: 'The source or content changed; this citation cannot be located precisely',
    referenceSourcePrevious: 'Previous citation location',
    referenceSourceNext: 'Next citation location',
    referenceSourceFoundPage: 'Found on page {page}',
    referenceSourceNotFound: 'Could not pinpoint the cited passage; the original is open',
    referenceSourceOpenWeb: 'Open the web page at this passage',
    chunkIdLabel: 'Chunk ID:',
    documentIdLabel: 'Document ID:',
    faqIdLabel: 'FAQ ID:',
    faqContainerIdLabel: 'Container ID:',
    faqAnswersLabel: 'Answers:',
    chunkOrdinal: 'Chunk {index}',
    previewContent: 'Preview content',
    noPlanSteps: 'No detailed steps provided',
    chunkIndexLabel: 'Chunk #{index}',
    chunkPositionLabel: '(Position: {position})',
    noRelatedChunks: 'No related chunks found',
    noSearchResults: 'No search results found',
    relevanceHigh: 'High relevance',
    relevanceMedium: 'Medium relevance',
    relevanceLow: 'Low relevance',
    relevanceWeak: 'Weak relevance',
    webSearchNoResults: 'No web search results found',
    otherSource: 'Other sources',
    webGroupIntro: 'The following {count} items are from',
    graphConfigTitle: 'Graph Configuration',
    entityTypesLabel: 'Entity types:',
    relationTypesLabel: 'Relation types:',
    graphResultsHeader: '{count} related results found',
    graphNoResults: 'No related graph information found',
    unknownLink: 'Unknown link',
    contentLengthLabel: 'Length {value}',
    notProvided: 'Not provided',
    errorMessageLabel: 'Error message',
    summaryLabel: 'Summary',
    rawTextLabel: 'Raw text',
    collapseRaw: 'Collapse original',
    expandRaw: 'Expand original',
    noWebContent: 'No web content fetched',
    webFetchStatusSuccess: 'Fetched',
    webFetchStatusFailed: 'Failed',
    webFetchStatusSkipped: 'Skipped',
    webFetchErrorCode: 'Error code',
    webFetchRetryable: 'Retryable',
    webFetchContentRange: 'Characters {start}–{end} of {total}',
    webFetchPartialContent: 'Partial page',
    webFetchSummaryFailed: 'Summary failed',
    lengthChars: '{value} characters',
    lengthThousands: '{value}k characters',
    lengthTenThousands: '{value} ten-thousand characters',
    noDatabaseRecords: 'No matching records found',
    nullValuePlaceholder: '<NULL>',
    chunkCountValue: '{count} chunks',
    documentDescriptionLabel: 'Description:',
    documentSourceLabel: 'Source:',
    documentFileLabel: 'File:',
    documentMetadataLabel: 'Metadata',
    documentInfoEmpty: 'No document information available',
    positionLabel: 'Position:',
    chunkPositionValue: 'Chunk #{index}',
    contentLengthLabelSimple: 'Content length:',
    fullContentLabel: 'Full content',
    copyContent: 'Copy content',
    knowledgeBaseCount: '{count} knowledge bases',
    noKnowledgeBases: 'No knowledge bases available',
    rawOutputLabel: 'Raw output',
    backgroundWork: {
      count: '{count} background tasks',
      states: {
        pending: 'Queued',
        running: 'Running',
        waiting: 'Waiting for input',
        succeeded: 'Completed',
        failed: 'Failed',
        cancelled: 'Cancelled',
        lost: 'Unavailable'
      },
      refresh: 'Refresh',
      structuredResult: 'Structured result',
      updateMessage: 'Additional task instructions',
      sendUpdate: 'Send update',
      stopRequested: 'Cancellation requested',
      actionFailed: 'Action failed. Try again.',
      cancelFailed: 'Cancellation failed. Try again.',
      stop: 'Stop',
      loading: 'Loading output…',
      unavailable: 'Output is unavailable'
    },
    wikiWritePageTitle: 'Wiki Page Write',
    wikiReplaceTextTitle: 'Wiki Text Replace',
    wikiRenamePageTitle: 'Wiki Page Rename',
    wikiDeletePageTitle: 'Wiki Page Delete',
    wikiActionCreated: 'Created',
    wikiActionUpdated: 'Updated',
    wikiActionRenamed: 'Renamed',
    wikiActionDeleted: 'Deleted',
    wikiFieldSlug: 'Slug',
    wikiFieldTitle: 'Title',
    wikiFieldPageType: 'Type',
    wikiFieldSummary: 'Summary',
    wikiFieldOldText: 'Old text',
    wikiFieldNewText: 'New text',
    wikiFieldOldSlug: 'Old slug',
    wikiFieldNewSlug: 'New slug',
    wikiFieldAffectedPages: 'Affected pages',
    wikiAffectedCount: '{count} page link(s) updated',
    processError: 'Processing error',
    sessionExcerpt: 'Session Excerpt',
    noAnswerContent: '(No answer content)',
    manualSourcesHeading: 'Sources',
    noMatchFound: 'No matching content found',
    deleteSessionFailed: 'Delete failed, please try again later!',
    imageTooMany: 'Maximum 5 images allowed',
    imageTypeSizeError: 'Only JPG/PNG/GIF/WEBP under 10MB supported',
    imageUploadTooltip: 'Upload image (paste/drop supported)',
    attachmentUploadTooltip: 'Upload attachment (documents, audio, etc.)',
    attachmentWithCount: '{count} attachment(s) uploaded',
    attachmentTooMany: 'Maximum {max} attachments allowed',
    attachmentTotalTooMany: 'Images and attachments combined can be at most {max}',
    attachmentTooLarge: 'File {name} exceeds {max}MB limit',
    attachmentTypeNotSupported: 'Unsupported file type: {name}',
    attachmentUploading: 'Uploading {progress}%',
    attachmentParsing: 'Parsing',
    attachmentReady: 'Ready',
    attachmentUploadFailed: 'Attachment upload failed',
    attachmentParseFailed: 'Attachment parsing failed',
    attachmentStillProcessing: 'Attachment {name} is still being parsed',
    memoryUsedCount: 'Used {count} memories',
    memoryForget: 'Delete this memory',
    memoryForgotten: 'Memory deleted',
    memoryForgetFailed: 'Failed to delete',
    memoryHint: 'These are the long-term memories this answer saw. Deleting one stops it from being used again.'
  },
  tenant: {
    title: 'Workspace Information',
    currentTenant: 'Current Workspace',
    switchTenant: 'Switch workspace',
    switcher: {
      menuLabel: 'Switch workspace',
      currentBadge: 'Current',
      homeTooltip: 'Your home workspace',
      empty: 'You only belong to one workspace'
    },
    statusActive: 'Active',
    statusInactive: 'Not activated',
    statusSuspended: 'Suspended',
    statusUnknown: 'Unknown',
    loadingInfo: 'Loading information...',
    retry: 'Retry',
    unknown: 'Unknown',
    formatError: 'Format error',
    searchPlaceholder: 'Search by name or enter workspace ID...',
    noMatch: 'No matching workspaces found',
    switchSuccessTitle: 'Workspace switched',
    switchSuccessContent: 'You are now in {name}',
    loadTenantsFailed: 'Failed to load workspace list',
    loading: 'Loading...',
    create: {
      action: 'Create new workspace',
      dialogTitle: 'Create new workspace',
      dialogSubtitle: 'This personal workspace includes 10 GB for your files. Accounts share the ContextDB knowledge bases.',
      nameLabel: 'Workspace name',
      namePlaceholder: 'e.g. My new project',
      nameRequired: 'Please enter a workspace name',
      descriptionLabel: 'Description (optional)',
      descriptionPlaceholder: 'Briefly describe what this workspace is for',
      submit: 'Create',
      cancel: 'Cancel',
      success: 'Workspace created successfully',
      failed: 'Failed to create workspace',
      disabled: 'This system only allows joining workspaces by invitation. You cannot create one yourself.'
    },
    details: {
      idLabel: 'Workspace ID',
      nameLabel: 'Workspace Name',
      descriptionLabel: 'Workspace Description',
      businessLabel: 'Workspace Business',
      statusLabel: 'Workspace Status',
      createdAtLabel: 'Workspace Creation Time',
      editName: 'Edit name',
      editNamePlaceholder: 'Enter the new workspace name',
      editNameConfirm: 'Save',
      editNameCancel: 'Cancel',
      editNameRequired: 'Workspace name cannot be empty',
      editNameSuccess: 'Workspace name updated',
      editNameFailed: 'Failed to update workspace name',
      editDescription: 'Edit description',
      editDescriptionPlaceholder: 'Enter the new workspace description',
      editDescriptionSuccess: 'Workspace description updated',
      editDescriptionFailed: 'Failed to update workspace description',
      descriptionEmptyPlaceholder: 'Not set'
    },
    storage: {
      usageLabel: 'Storage Usage'
    },
    leaveDangerZone: {
      title: 'Leave this workspace',
      desc: 'Ends your membership in this workspace. You will lose access to its knowledge bases and agents. You can be invited again later.',
      button: 'Leave workspace'
    },
    deleteDangerZone: {
      title: 'Delete this workspace',
      desc: 'Deleting this workspace removes access to its personal files, conversations and agent settings. You keep your account and shared knowledge bases.',
      button: 'Delete workspace',
      confirmTitle: 'Delete this workspace?',
      confirmBody: 'Permanently delete “{name}”? You keep your account and shared knowledge bases.',
      confirmHint: 'Type the workspace name "{name}" to confirm deletion.',
      confirm: 'Delete workspace',
      nameMismatch: 'Workspace name does not match',
      success: 'Workspace deleted',
      failed: 'Failed to delete workspace'
    },
    messages: {
      fetchFailed: 'Failed to fetch workspace information',
      networkError: 'Network error, please try again later'
    },
    api: {
      title: 'API Information',
      userIdLabel: 'User ID',
      userIdDescription: 'Your unique user identifier',
      usernameLabel: 'Username',
      usernameDescription: 'Your login username',
      createdAtLabel: 'Registration Time',
      createdAtDescription: 'Time when the account was created'
    }
  },
  system: {
    globalSettings: {
      title: 'System Settings',
      runtime: {
        tasks: {
          taskTypes: {
            documentProcess: 'Document parsing',
            manualProcess: 'Manual reprocessing',
            temporaryDocumentProcess: 'Chat attachment parsing',
            postProcess: 'Document post-processing',
            summary: 'Summary generation',
            tableSummary: 'Table summary generation',
            question: 'Question generation',
            multimodal: 'Image multimodal processing',
            graph: 'Knowledge graph extraction',
            sync: 'Data-source sync',
            faqImport: 'FAQ import',
            batchReparse: 'Batch reparse',
            batchDelete: 'Batch delete',
            move: 'Document move',
            indexDelete: 'Index deletion',
            kbClone: 'Knowledge-base clone',
            kbDelete: 'Knowledge-base deletion',
            wikiIngest: 'Wiki content generation',
            wikiFinalize: 'Wiki finalization'
          }
        },
        pools: {
          core: 'Core parsing',
          postprocess: 'Post-process orchestration',
          enrichment: 'Enrichment',
          maintenance: 'Maintenance & sync',
          shared: 'Shared elastic',
          wiki: 'Wiki pool'
        },
        poolDescriptions: {
          core: 'Guaranteed document and manual parsing capacity',
          postprocess: 'Parse finalization and enrichment fan-out',
          enrichment: 'Summaries, images, graph, and question generation',
          maintenance: 'Source sync, batch work, and deletion cleanup',
          shared: 'Borrowed by core or enrichment according to backlog',
          wiki: 'Wiki content generation and global finalization'
        },
        queueNames: {
          default: 'Document parsing',
          chat_attachment: 'Chat attachments',
          postprocess: 'Post-process',
          summary: 'Summaries',
          sync: 'Source sync',
          low: 'Maintenance & batch',
          multimodal: 'Multimodal',
          graph: 'Graph extraction',
          question: 'Questions',
          wiki: 'Wiki pipeline'
        },
        queueDescriptions: {
          default: 'Document parse, manual reparse',
          chat_attachment: 'Session-scoped chat upload parsing',
          postprocess: 'Parse finalization, enrichment fan-out',
          summary: 'Document & table summaries',
          sync: 'Manual & scheduled sync',
          low: 'FAQ import, batch reparse, cleanup',
          multimodal: 'Image OCR, vision captions',
          graph: 'Chunk-level graph extraction',
          question: 'Chunk-level question generation',
          wiki: 'Content generation, index finalize'
        }
      },
      keyLabels: {
        auth: {
          registration_mode: 'Registration mode',
          default_tenant_mode: 'Default workspace provisioning',
          complex_password_enabled: 'Require complex password'
        },
        ssrf: {
          whitelist: 'SSRF protection allowlist'
        },
        sandbox: {
          docker_enabled: 'Enable Docker sandbox'
        },
        tenant: {
          max_owned_per_user: 'Max workspaces owned per user',
          self_service_creation_enabled: 'Allow self-service workspace creation',
          default_storage_quota_gb: 'Default storage quota for new workspaces (GB)',
          default_storage_quota_mb: 'Default storage quota for new workspaces (MB)',
          auto_create_api_key: 'Automatically create an API key for new workspaces',
          auto_accept_invitation: 'Auto-join invited registered users'
        },
        asynq: {
          core_concurrency: 'Guaranteed core parse concurrency',
          postprocess_concurrency: 'Post-process concurrency',
          enrichment_concurrency: 'Guaranteed enrichment concurrency',
          maintenance_concurrency: 'Maintenance concurrency',
          shared_concurrency: 'Shared elastic concurrency',
          wiki_concurrency: 'Wiki worker concurrency'
        },
        model: {
          max_concurrency: 'Default per-model concurrency limit'
        }
      },
      keyDescriptions: {
        auth: {
          registration_mode: 'Registration mode. Open registration allows anyone to create an account; invitation registration requires a valid invitation link; disabled registration prevents account creation while existing accounts can still accept invitations. Changes take effect immediately.',
          default_tenant_mode: 'Workspace provisioning after public registration. create_personal creates an Owner workspace; tenantless creates only the account until the user accepts an invitation or creates a workspace. Applies to new users only.',
          complex_password_enabled: 'Whether to require complex passwords. When enabled, passwords must contain uppercase and lowercase letters, numbers, and special characters. Changes take effect immediately and only apply to newly registered users or new password changes/resets. Special characters include {specialChars}'
        },
        ssrf: {
          whitelist: 'SSRF protection allowlist. Accepts entries such as example.com / *.foo.com / 10.0.0.0/8 / 2001:db8::1. Takes effect immediately after saving. The SSRF_WHITELIST_EXTRA environment variable is still maintained by the deployer and is not overridden here.'
        },
        sandbox: {
          docker_enabled: 'Allow the Docker sandbox backend. A local docker.sock is equivalent to root on the host, so this stays off by default. Only a system admin can turn it on; the change takes effect immediately. Enable it only on a private single-node install that mounts the daemon socket or uses a TLS-protected remote tcp:// endpoint.'
        },
        tenant: {
          max_owned_per_user: 'Maximum number of workspaces a non-superuser may own via self-service creation. Read on every workspace creation and takes effect immediately after saving. 0 uses the built-in default of 10; a negative value disables the cap entirely (not recommended on public deployments).',
          self_service_creation_enabled: 'Whether non-superusers may create workspaces themselves. When disabled, regular users can only join existing workspaces by invitation; cross-workspace superusers remain exempt. Takes effect immediately.',
          default_storage_quota_gb: 'Default storage quota (GB) assigned when a new workspace is created, covering vectors, originals, text, indexes, and related data. Read only at creation time — changes apply to newly created workspaces only and do not retroactively update existing workspaces. 0 or a negative value uses the built-in default of 10 GB.',
          default_storage_quota_mb: 'Includes personal workspaces created at registration. Positive values override the GB setting; zero or negative values use GB. Each setting resolves from database, environment, then built-in default. Changes affect newly created workspaces only.',
          auto_create_api_key: 'Automatically creates a full_access API key for a new workspace and returns its plaintext token in the create response. Use only for integrations that depend on the legacy behavior; it is disabled by default and explicit API-key creation is recommended.',
          auto_accept_invitation: 'When enabled, inviting a registered user by email adds them as a member immediately instead of waiting for inbox confirmation. When off, the invitee must accept from their inbox. Takes effect immediately.'
        },
        asynq: {
          core_concurrency: 'Guaranteed per-process concurrency for document and manual parsing. Core may also borrow the shared elastic pool. Minimum 1; requires a service restart.',
          postprocess_concurrency: 'Dedicated per-process concurrency for lightweight parse finalization and enrichment fan-out. Minimum 1; requires a service restart.',
          enrichment_concurrency: 'Guaranteed per-process concurrency for summaries, images, graph, and question generation. Enrichment may also borrow the shared elastic pool. Minimum 1; requires a service restart.',
          maintenance_concurrency: 'Per-process concurrency for source sync, batch work, and cleanup, hard-isolated from the user-facing pipeline. Minimum 1; requires a service restart.',
          shared_concurrency: 'Per-process elastic concurrency shared by core parsing and enrichment; whichever side has backlog borrows it automatically. Minimum 1; requires a service restart.',
          wiki_concurrency: 'Per-process concurrency for the dedicated Wiki worker pool, isolated from upstream tasks. Minimum 1; requires a service restart.'
        },
        model: {
          max_concurrency: 'Default cap on concurrent background (ingestion/enrichment) calls to a single model, keyed by model ID and shared across replicas. Read on every call and applied immediately with no restart. 0 or a negative value disables the default cap (each model still honours its own limit configured in model management). Affects background tasks only, not interactive chat.'
        }
      },
      enumLabels: {
        auth: {
          registration_mode: {
            self_serve: 'Self-service (anyone can register)',
            invite_register: 'Invitation registration (valid link required)',
            invite_only: 'Registration disabled (existing accounts can accept invitations)'
          },
          default_tenant_mode: {
            create_personal: 'Create personal workspace',
            tenantless: 'Do not create a workspace'
          }
        }
      },
      listConfirm: {
        ssrf: {
          whitelist: {
            add: {
              header: 'Add SSRF allowlist entry',
              body: 'Add {entry} to the SSRF allowlist? Hosts / IPs / CIDRs that match this entry will bypass SSRF protection and may let agents reach internal services. Only add entries you fully trust.',
              confirmBtn: 'Add'
            },
            remove: {
              header: 'Remove SSRF allowlist entry',
              body: 'Remove {entry} from the SSRF allowlist? After removal this entry will be blocked by SSRF protection again.',
              confirmBtn: 'Remove'
            }
          }
        }
      },
      audit: {
        actorRole: {
          system_admin: 'System Admin'
        },
        action: {
          'system.setting_changed': 'System setting changed',
          'system.admin_promoted': 'System admin granted',
          'system.api_key_created': 'Platform API key created',
          'system.api_key_revoked': 'Platform API key revoked',
          'system.admin_revoked': 'System admin revoked',
          'system.user_password_reset': 'User password reset',
          'system.user_created': 'User created',
          'system.queue_task_retried': 'Failed task run again',
          'system.queue_task_deleted': 'Failed task record cleared',
          'system.queue_task_run_now': 'Queue task run now',
          'system.queue_task_cancelled': 'Queue task cancelled',
          'system.queue_archived_purged': 'All failed tasks cleared'
        }
      }
    }
  },
  mcp: {
    testResult: {
      title: 'Test Result: {name}'
    }
  },
  error: {
    networkError: 'Network error, please check your connection',
    invalidCredentials: 'Invalid username or password',
    tokenRefreshFailed: 'Token refresh failed',
    pleaseRelogin: 'Please log in again',
    fileSizeExceeded: 'File size cannot exceed {size}MB!',
    unsupportedFileType: 'Unsupported file type!',
    invalidImageLink: 'Invalid image link',
    tokenNotFound: 'Login token not found, please log in again',
    streamFailed: 'Stream connection failed',
    auth: {
      loginFailed: 'Login failed',
      registerFailed: 'Registration failed',
      getUserFailed: 'Failed to get user info',
      getTenantFailed: 'Failed to get workspace info',
      updatePreferencesFailed: 'Failed to update preferences',
      refreshTokenFailed: 'Token refresh failed',
      logoutFailed: 'Logout failed',
      validateTokenFailed: 'Token validation failed'
    },
    model: {
      createFailed: 'Failed to create model',
      getFailed: 'Failed to get model',
      updateFailed: 'Failed to update model',
      deleteFailed: 'Failed to delete model'
    },
    tenant: {
      listFailed: 'Failed to list workspaces',
      searchFailed: 'Failed to search workspaces',
      getApiPrincipalConfigFailed: 'Failed to get API principal config',
      updateApiPrincipalConfigFailed: 'Failed to update API principal config',
      createApiPrincipalTestTokenFailed: 'Failed to create API test token',
      updateFailed: 'Failed to update workspace information',
      deleteFailed: 'Failed to delete workspace'
    },
    initialization: {
      checkFailed: 'Check failed',
      testFailed: 'Test failed'
    }
  },
  model: {
    modelName: 'Model Name',
    defaultTag: 'Default',
    addModelInSettings: 'Go to global settings to add models',
    loadFailed: 'Failed to load model list',
    selectModelPlaceholder: 'Select a model',
    editor: {
      legacyLocalUnavailable: 'Legacy Ollama service management is retired. The saved record is preserved. To use a local model, select API and enter its OpenAI-compatible endpoint.',
      maxOutputTokensLabel: 'Max output tokens',
      maxOutputTokensPlaceholder: 'Leave empty for the catalog default',
      maxOutputTokensDesc: 'Output cap per response. Leave empty to use the catalog default for this model.',
      catalog: {
        reasoning: 'Reasoning',
        vision: 'Vision',
        hint: 'Pick a model from the vendor catalog or type a custom model name.'
      },
      resolved: {
        title: 'How this model is called',
        empty: 'Fill in the vendor and model name to see how this model will be called',
        failed: 'Resolve failed',
        protocol: 'Request protocol',
        catalog: 'Capabilities from',
        catalogedYes: 'Built-in model profile',
        catalogedNo: 'Vendor defaults (model not in the catalog)',
        endpoint: 'Request endpoint',
        thinkingFormat: 'Thinking switch sent as',
        thinkingLevels: 'Selectable effort',
        noThinking: 'This model cannot think'
      },
      advanced: {
        toggle: 'Advanced',
        api: {
          label: 'Protocol override',
          auto: 'Auto (from vendor / URL)',
          desc: 'Force a request protocol; normally unnecessary.'
        },
        remoteModelName: {
          label: 'Remote model name',
          placeholder: 'Leave empty to use the model name',
          desc: 'Model id actually sent to the vendor when it differs from the name above.'
        },
        legacyThinking: {
          label: 'Thinking parameter format (legacy)',
          catalog: 'Follow catalog default (recommended)',
          none: 'Do not send thinking fields',
          desc: 'This model still carries a legacy thinking_control setting. Choose "Follow catalog default" to let the catalog decide.'
        },
        compat: {
          label: 'Protocol compat override (JSON)',
          placeholder: '{\'{\'} "max_tokens_field": "max_tokens" {\'}\'}',
          desc: 'Only needed when the endpoint differs from the catalog defaults; include just the fields to change. Leave empty for no override.',
          docLink: 'Field reference',
          invalid: 'Invalid JSON',
          mustBeObject: 'Must be a JSON object'
        }
      },
      addTitle: 'Add Model',
      editTitle: 'Edit Model',
      sectionType: 'Model Type',
      typeLabel: 'Model Type',
      sectionSource: 'Source',
      sectionProvider: 'Provider Settings',
      sectionAdvanced: 'Advanced Options',
      sourceLabel: 'Model Source',
      sourceRemote: 'API',
      description: {
        chat: 'Configure large language models for conversations',
        embedding: 'Configure embedding models for text vectorization',
        rerank: 'Configure models for result re-ranking',
        vllm: 'Configure vision-language models for multimodal understanding',
        asr: 'Configure speech-to-text models for audio transcription',
        default: 'Configure model information'
      },
      modelNamePlaceholder: {
        remote: 'e.g. gpt-4, claude-3-opus',
        remoteVllm: 'e.g. gpt-4-vision-preview',
        remoteAsr: 'e.g. whisper-1'
      },
      baseUrlLabel: 'Base URL',
      displayNameLabel: 'Display name (optional)',
      displayNamePlaceholder: 'e.g. Support QA model',
      displayNameDesc: 'Used only in the UI. Runtime calls still use the model name above.',
      baseUrlPlaceholder: 'e.g. https://api.openai.com/v1',
      baseUrlPlaceholderVllm: 'e.g. http://localhost:11434/v1',
      baseUrlPlaceholderAsr: 'e.g. https://api.openai.com/v1',
      apiKeyOptional: 'API Key (optional)',
      apiKeyPlaceholder: 'Enter API Key',
      customHeadersLabel: 'Custom Request Headers (optional)',
      customHeadersDesc: 'Extra HTTP headers appended to requests to the remote model API (e.g. for enterprise gateway auth or tracing). Reserved headers like Authorization / Content-Type are ignored.',
      customHeadersAdd: 'Add Header',
      customHeadersKeyPlaceholder: 'Header name',
      customHeadersValuePlaceholder: 'Header value',
      testing: 'Testing...',
      testConnection: 'Test Connection',
      dimensionLabel: 'Vector Dimension',
      dimensionPlaceholder: 'e.g. 1536',
      dimensionOverrideLabel: 'Custom Output Dimension',
      dimensionOverrideDesc: 'Enable only if the provider documentation says this model accepts a dimensions parameter.',
      supportsVisionLabel: 'Supports Vision / Multimodal',
      supportsVisionDesc: 'Whether the model accepts image and multimodal input',
      embeddingImageInputLabel: 'Image Input',
      embeddingImageInputDesc: 'The model embeds images into the same vector space as text. Catalogued models are detected automatically; declare it for custom models',
      contextWindowLabel: 'Context Window',
      contextWindowPlaceholder: 'Enter the provider’s total context window',
      contextWindowDesc: 'The total context window for one request. Advanced spec overrides this value; an empty value with no spec remains unknown. Use the provider’s documented limit. The agent reserves output tokens and compaction headroom.',
      contextWindowUnknown: 'Unknown',
      contextWindowTokens: '{count} tokens',
      maxConcurrencyLabel: 'Background concurrency limit',
      maxConcurrencyPlaceholder: '0 = use global default',
      maxConcurrencyDesc: 'Caps concurrent background (ingestion/enrichment) calls to this model, shared per model across all replicas. 0 or empty falls back to the global default; interactive chat is never affected.',
      fillModelAndUrl: 'Please fill in the model identifier and Base URL first',
      remoteBaseUrlRequired: 'Remote API type requires a Base URL',
      unsupportedModelType: 'Unsupported model type',
      saveAndClose: 'Save and close',
      testDraftHint: 'Test the current connection settings without saving first.',
      testDraftEditHint: 'Test the current connection settings using the API key saved separately.',
      testStale: 'Settings changed. Run the test again.',
      connectionSuccess: 'Connection succeeded',
      connectionFailed: 'Connection failed',
      connectionConfigError: 'Connection failed, please check the configuration',
      validation: {
        extraFieldRequired: 'Please fill in {name}',
        modelNameRequired: 'Please enter the model name',
        modelNameEmpty: 'Model name cannot be empty',
        modelNameMax: 'Model name cannot exceed 100 characters',
        baseUrlRequired: 'Please enter the Base URL',
        baseUrlEmpty: 'Base URL cannot be empty',
        baseUrlInvalid: 'Invalid Base URL, please enter a valid URL'
      },
      providerLabel: 'Provider',
      providerPlaceholder: 'Select model provider',
      providerDocs: 'Read the {provider} model docs'
    },
    builtinTag: 'Built-in'
  },
  language: {
    zhCN: '简体中文',
    zhTW: 'Traditional Chinese',
    enUS: 'English',
    ruRU: 'Русский',
    koKR: '한국어',
    jaJP: '日本語',
    selectLanguage: 'Select Language',
    language: 'Language',
    languageDescription: 'Select interface display language',
    languageSaved: 'Language settings saved'
  },
  general: {
    title: 'General Settings',
    personalSettings: 'Personal Settings',
    description: 'Configure language, appearance and other basic options',
    close: 'Close Settings'
  },
  theme: {
    theme: 'Theme',
    themeDescription: 'Choose the display theme for the interface, supports automatic switching with system settings',
    light: 'Light',
    dark: 'Dark',
    system: 'Follow System',
    selectTheme: 'Select theme'
  },
  font: {
    uiFont: 'Interface Font',
    uiFontDescription: 'Font used for menus, body text, buttons, and most UI text',
    monoFont: 'Code Font',
    monoFontDescription: 'Used for code blocks, terminal commands, API keys, file paths and other technical text. Every character has the same width so you can tell 0 from O and 1 from l.',
    selectFont: 'Select font',
    sansPreview: 'The quick brown fox jumps — Aa Gg Oo 0123',
    monoPreview: 'const msg = \'Hello\'; // 0O1l',
    sans: {
      system: 'System Default',
      pingfang: 'PingFang SC',
      georgia: 'Georgia (Serif)',
      yahei: 'Microsoft YaHei',
      times: 'Times New Roman (Serif)',
      'noto-cjk': 'Noto Sans CJK',
      'dejavu-serif': 'DejaVu Serif (Serif)',
      'sans-serif': 'Generic Sans-Serif'
    },
    mono: {
      system: 'System Default',
      menlo: 'Menlo',
      monaco: 'Monaco',
      consolas: 'Consolas',
      cascadia: 'Cascadia Code',
      'dejavu-mono': 'DejaVu Sans Mono',
      'liberation-mono': 'Liberation Mono',
      monospace: 'Generic Monospace'
    },
    fontSize: 'Font Size',
    fontSizeDescription: 'Scales the entire interface (text, icons, spacing) and applies immediately',
    size: {
      small: 'Small',
      normal: 'Normal',
      large: 'Large'
    }
  },
  platform: {
    loginShowcase: {
      carouselLabel: 'Renwoxing knowledge base feature illustration',
      switchLabel: 'Switch feature topic',
      pause: 'Pause carousel and flow animation',
      play: 'Play carousel and flow animation',
      reducedMotion: 'Autoplay stopped to respect reduced motion',
      themes: {
        query: {
          title: 'Every answer has a source',
          description: 'Ask naturally and find answers grounded in your documents',
          summary: 'A question finds relevant source material, then reveals an answer with its citation.',
          mobile: 'Question → Source material → Cited answer',
          tab: 'Cited answers'
        },
        organization: {
          title: 'Scattered documents, connected knowledge',
          description: 'Organize materials by topic and connect related knowledge',
          summary: 'Source materials are organized into product knowledge, implementation and customer service topics.',
          mobile: 'Source materials → Product / Delivery / Service knowledge',
          tab: 'Organization'
        },
        intake: {
          title: 'Company knowledge, brought together',
          description: 'Connect documents, web pages and existing knowledge platforms',
          summary: 'Documents, web pages and existing knowledge come together in one knowledge entry point.',
          mobile: 'Documents / Web / Existing knowledge → One entry point',
          tab: 'Collection'
        },
        review: {
          title: 'Keep knowledge up to date',
          description: 'Review content changes so knowledge continues to be useful',
          summary: 'Content changes are reviewed and confirmed before the corresponding knowledge is updated.',
          mobile: 'Content change → Knowledge review → Knowledge update',
          tab: 'Review & update'
        }
      },
      labels: {
        query: 'Question',
        sourceHit: 'Source found',
        citedAnswer: 'Cited answer',
        sourceMaterial: 'Sources',
        productKnowledge: 'Product',
        delivery: 'Delivery',
        customerService: 'Support',
        documents: 'Documents',
        webContent: 'Web',
        existingKnowledge: 'Knowledge',
        knowledgeEntry: 'Knowledge hub',
        materialsReceived: 'Collected',
        contentChange: 'Changes',
        knowledgeReview: 'Review',
        knowledgeUpdate: 'Updated',
        updateConfirmed: 'Update confirmed'
      }
    },
    multimodalParsing: 'Multimodal Document Parsing',
    hybridSearchEngine: 'Hybrid Search + Knowledge Graph',
    ragQandA: 'ReAct Agent Q&A',
    independentTenant: 'Independent Workspace',
    fullApiAccess: 'Full API Access',
    knowledgeBaseManagement: 'Knowledge Base Management'
  },
  time: {
    today: 'Today',
    yesterday: 'Yesterday',
    last7Days: 'Last 7 Days',
    last30Days: 'Last 30 Days',
    lastYear: 'Last Year',
    earlier: 'Earlier',
    pinned: 'Pinned'
  },
  upload: {
    uploadDocument: 'Upload Document',
    uploadFolder: 'Upload Folder',
    onlineEdit: 'Online Edit',
    deleteRecord: 'Delete Record'
  },
  uploadTasks: {
    panelLabel: 'Uploads',
    titleUploading: 'Uploading {done} of {total}',
    titleParsing: 'Parsing {done} of {total}',
    titleDone: 'All done',
    titleDoneWithIssues: '{ok} done, {bad} not completed',
    titleCancelled: 'Upload cancelled',
    destination: 'Destination: {name}',
    destinationMany: 'Destination: {count} knowledge bases',
    remaining: 'about {time} left',
    eta: {
      seconds: '{n} sec',
      minutes: '{n} min',
      hours: '{n} hr'
    },
    hintUploading: 'Keep this page open until the upload finishes',
    hintParsing: 'All files are uploaded. Parsing continues in the background, so you can leave this page',
    legend: {
      ready: 'Searchable',
      active: 'In progress',
      waiting: 'Queued',
      failed: 'Failed',
      duplicate: 'Already exists'
    },
    filterAll: 'All',
    filterIssues: 'Not completed',
    phaseWaiting: 'Queued',
    phaseSaving: 'Saving…',
    phasePending: 'Waiting to parse',
    phaseReady: 'Done',
    phaseParseFailed: 'Parsing failed',
    phaseDuplicate: 'Same file already in this knowledge base',
    phaseCancelled: 'Cancelled',
    cancel: 'Cancel',
    cancelAll: 'Cancel all',
    retry: 'Retry',
    retryFailed: 'Retry ({count})',
    open: 'Open',
    collapse: 'Collapse',
    expand: 'Expand',
    close: 'Close',
    closeConfirm: 'Closing stops the unfinished uploads ({count})',
    closeConfirmOk: 'Cancel upload',
    closeConfirmKeep: 'Keep uploading'
  },
  agentSettings: {
    modelRecommendation: {
      title: 'Model Recommendation'
    },
    maxIterations: {
      desc: 'Caps how many reasoning steps one task may take. Unlimited keeps going until the model stops on its own or you stop it.'
    },
    thinkingModel: {
      desc: 'LLM used for Agent reasoning and planning'
    },
    rerankModel: {
      desc: 'Re-rank search results and normalize relevance scores'
    },
    temperature: {
      desc: 'Controls randomness in outputs. 0 is most deterministic; 1 is most random'
    },
    allowedTools: {
      desc: 'Tools currently enabled for the Agent'
    },
    systemPrompt: {
      desc: 'Configure the Agent’s system prompt with placeholders that are resolved at runtime.'
    }
  },
  conversationSettings: {
    models: {
      chatGroupLabel: 'Thinking / Chat Models'
    },
    maxRounds: {
      desc: 'Number of rounds kept for context and query rewrite'
    },
    embeddingTopK: {
      desc: 'Number of documents kept after vector retrieval'
    },
    keywordThreshold: {
      desc: 'Minimum score for keyword retrieval'
    },
    vectorThreshold: {
      desc: 'Minimum similarity for vector retrieval'
    },
    rerankTopK: {
      desc: 'Documents kept after re-ranking'
    },
    rerankThreshold: {
      desc: 'Minimum score required after re-ranking'
    },
    enableRewrite: {
      desc: 'Automatically rewrite multi-turn queries for better recall'
    },
    enableQueryExpansion: {
      desc: 'When recall is low, call a reasoning model to generate expansion queries (adds latency & cost)'
    },
    fallbackStrategy: {
      desc: 'How to respond when no relevant documents are found'
    },
    fallbackResponse: {
      desc: 'Text returned when using the fixed fallback strategy'
    },
    fallbackPrompt: {
      desc: 'Prompt used when fallback strategy is "model"'
    },
    rewritePrompt: {
      desc: 'System prompt used during query rewrite'
    },
    chatModel: {
      desc: 'Large language model used for summarization and abstract generation'
    },
    rerankModel: {
      desc: 'Model for re-ranking search results (optional)'
    },
    contextTemplate: {
      desc: 'Prompt template for generating answers based on retrieval results in normal mode'
    },
    systemPrompt: {
      desc: 'System-level prompt for normal mode conversations'
    },
    temperature: {
      desc: 'Controls randomness in outputs. 0 is most deterministic; 1 is most random'
    },
    maxTokens: {
      desc: 'Maximum number of tokens to generate in the response'
    }
  },
  mcpSettings: {
    addUsageInstructions: 'Add usage instructions',
    noUsageInstructions: 'No usage instructions yet',
    title: 'MCP Services',
    description: 'Manage external MCP (Model Context Protocol) services for tools/resources in Agent mode',
    enabled: 'Enabled',
    disabled: 'Disabled',
    addService: 'Add Service',
    empty: 'No MCP services',
    toasts: {
      loadFailed: 'Failed to load MCP services',
      enabled: 'MCP service enabled',
      disabled: 'MCP service disabled',
      updateStateFailed: 'Failed to update MCP service status',
      linkedServiceMissing: 'The MCP service the assistant linked to was not found; it may have been deleted',
      deleted: 'MCP service deleted',
      deleteFailed: 'Failed to delete MCP service'
    },
    deleteConfirmBody: 'Delete MCP service "{name}"? This action cannot be undone.',
    unnamed: 'Unnamed',
    builtin: 'Built-in',
    toolCount: '{count} tools',
    toolsNotSynced: 'Tools not synced',
    toolsStale: 'Needs resync'
  },
  modelSettings: {
    moreActions: 'More actions',
    title: 'Model Settings',
    typeShort: {
      chat: 'Chat',
      embedding: 'Embedding',
      rerank: 'ReRank',
      vllm: 'Vision',
      asr: 'Speech'
    },
    actions: {
      addModel: 'Add Model',
      debugModel: 'Model Test'
    },
    source: {
      remote: 'Remote',
      openaiCompatible: 'OpenAI-compatible',
      custom: 'Custom'
    },
    chat: {
      title: 'Chat Models',
      desc: 'Configure large language models for chatting',
      empty: 'No chat models'
    },
    embedding: {
      title: 'Embedding Models',
      desc: 'Configure embedding models for text vectorization',
      empty: 'No embedding models'
    },
    rerank: {
      title: 'ReRank Models',
      desc: 'Configure models for result re-ranking',
      empty: 'No re-rank models'
    },
    vllm: {
      title: 'VLLM Vision Models',
      desc: 'Configure vision-language models for multimodal understanding',
      empty: 'No VLLM models'
    },
    asr: {
      title: 'ASR Speech Models',
      desc: 'Configure speech-to-text models for audio transcription (e.g. OpenAI Whisper)',
      empty: 'No ASR models'
    },
    toasts: {
      nameRequired: 'Model name cannot be empty',
      nameTooLong: 'Model name cannot exceed 100 characters',
      displayNameTooLong: 'Display name cannot exceed 100 characters',
      baseUrlRequired: 'Base URL is required for remote APIs',
      baseUrlInvalid: 'Invalid Base URL, please enter a valid URL',
      dimensionInvalid: 'Embedding dimension must be between 128 and 4096',
      updated: 'Model updated',
      added: 'Model added',
      saveFailed: 'Failed to save model',
      deleted: 'Model deleted',
      deleteFailed: 'Failed to delete model',
      builtinCannotEdit: 'Built-in models cannot be edited',
      linkedModelMissing: 'The model the assistant linked to was not found; it may have been deleted',
      builtinCannotDelete: 'Built-in models cannot be deleted',
      builtinCannotCopy: 'Built-in models cannot be copied',
      copied: 'Model copied',
      copyFailed: 'Failed to copy model'
    },
    copySuffix: ' Copy',
    builtinModels: {
      title: 'Built-in Models',
      description: 'Built-in models are visible to all workspaces. Sensitive information is hidden, and they cannot be edited or deleted.',
      descriptionAdmin: 'Built-in models are visible to all workspaces. System administrators can edit configuration and credentials; deletion remains deployment-managed.',
      viewGuide: 'View Built-in Models Guide'
    },
    builtinTag: 'Built-in',
    confirmDelete: 'Delete model "{name}"?',
    usage: {
      title: 'Model cannot be deleted',
      description: 'Model "{name}" is still referenced by the following settings. Open each configuration and choose another model before deleting it.',
      knowledgeBases: 'Knowledge bases ({count})',
      agents: 'Agents ({count})',
      openConfiguration: 'Open settings',
      truncated: 'Showing the first {shown} of {total}',
      longTermMemory: 'Long-term memory'
    },
    debug: {
      reasoningEffort: 'Reasoning effort',
      reasoningEffortDesc: 'Sends reasoning_effort using the levels reported by the model catalog',
      title: 'Model Test',
      description: 'Send a real request using saved model settings. Save pending edits before testing here.',
      groupModel: 'Select model',
      groupInput: 'Test input',
      groupResult: 'Result',
      modelType: 'Model type',
      model: 'Model',
      modelPlaceholder: 'Select a model to test',
      noModelsForType: 'No saved models of this type',
      query: 'Input',
      queryPlaceholder: 'Enter the text to send to the model',
      embeddingInput: 'Text to embed',
      embeddingPlaceholder: 'Enter text to generate an embedding',
      vlmPrompt: 'Image prompt',
      vlmPromptPlaceholder: 'For example: Describe this image in detail',
      documents: 'Candidate documents',
      documentsPlaceholder: 'Enter one candidate document per line',
      documentsHint: 'Each non-empty line is sent as a separate document to the ReRank model',
      imageFile: 'Image file',
      similarityMode: 'Similarity',
      similarityQuery: 'Query',
      similarityQueryPlaceholder: 'Enter a query, e.g. a dog running on grass',
      similarityCandidates: 'Candidates',
      similarityCandidatesPlaceholder: 'One candidate text per line',
      similarityHint: 'The query is embedded as a search query and the candidates as documents, as in retrieval; results are sorted by cosine similarity, highest first',
      similarityImage: 'Candidate image (optional)',
      similarityImageCandidate: 'Image',
      audioFile: 'Audio file',
      chooseFile: 'Choose file',
      parameters: 'Request parameters',
      systemPrompt: 'System Prompt',
      systemPromptPlaceholder: 'Optional system prompt',
      run: 'Run test',
      copyResult: 'Copy result',
      history: 'History',
      runLabel: 'Run #{n}',
      success: 'Request succeeded',
      failed: 'Request failed',
      rawResponse: 'Response',
      requestPreview: 'Request preview',
      requestFailed: 'Model test request failed',
      metrics: {
        api: 'Protocol',
        thinkingFormat: 'Thinking format',
        requestedReasoningEffort: 'Requested effort',
        dimension: 'Dimensions',
        resultCount: 'Result count',
        answerChars: 'Answer chars',
        reasoningChars: 'Reasoning chars',
        reasoningReturned: 'Reasoning returned',
        textChars: 'Transcript chars',
        segmentCount: 'Segment count'
      }
    }
  },
  ollamaSettings: {
    status: {
      desc: 'Automatically detect local Ollama service availability. If the service is down or the URL is incorrect, status will be "Unavailable".'
    },
    address: {
      desc: 'The API address of the local Ollama service, auto-detected by the system. To modify, set it in the .env file.'
    },
    download: {
      title: 'Download Models'
    },
    installed: {
      title: 'Installed Models',
      desc: 'Models installed in Ollama'
    }
  },
  mcpMetadata: {
    searchTools: 'Search tool names or descriptions',
    retry: 'Retry',
    details: 'Details',
    description: 'Description',
    parameters: 'Parameters',
    required: 'Required',
    fullSchema: 'Full definition',
    noDescription: 'No description',
    noParameters: 'No parameter definition',
    enabled: 'Enabled',
    approval: 'Require approval',
    noTools: 'No matching tools',
    next: 'Next',
    policyLoadFailed: 'Could not load tool policies. Retry before editing.',
    policySaveFailed: 'Could not save tool settings',
    tools: 'Tools',
    cacheHint: 'This step connects automatically if no directory is saved yet. Later visits only connect when you refresh.',
    fetch: 'Fetch again',
    fetching: 'Connecting and fetching tools…',
    toolCount: '{count} tools',
    stale: 'Connection or authentication settings changed. Refresh this old directory before models can use it.',
    notSynced: 'No tools synchronized yet. Fetch to save full descriptions and parameter definitions.',
    syncRequired: 'Connect and fetch tools first. Models can only use a synchronized directory.',
    syncedAt: 'Last synchronized:',
    serverDocumentation: 'Original server documentation',
    noServerDocumentation: 'This MCP server\'s initialize result did not include instructions or serverInfo.description (both are optional). Tool text lives in each tool\'s description below.',
    policyHint: 'Tool and approval switches save immediately and survive directory refreshes.',
    columnTool: 'Tool',
    columnEnabled: 'Enabled',
    columnApproval: 'Approval',
    failed: 'Could not load the tool directory',
    setupProgress: 'MCP setup steps',
    connection: 'Connection',
    toolsAndUsage: 'Tools and usage',
    previous: 'Previous',
    usage: 'Service usage',
    usageHint: 'Models read this overview before loading specific tools. Your text is preserved when refreshing.',
    usageInstructions: 'Usage instructions',
    instructionsPlaceholder: 'Briefly describe the purpose, use cases, and key constraints.',
    generateUsage: 'Generate with AI',
    generateHint: 'Generate concise instructions from synced, enabled tools. Edit the result and save to apply it.',
    instructionsRequired: 'Usage instructions are required',
    generated: 'Generated. Review and save to apply.',
    generateFailed: 'Generation failed. Check that tools are synced and an active chat model is configured, then retry.'
  },
  mcpServiceDialog: {
    addTitle: 'Add MCP Service',
    addDesc: 'Connect an external MCP service so agents can call its tools.',
    editTitle: 'Edit MCP Service',
    basicSection: 'Basic',
    connectionSection: 'Connection',
    enableServiceDesc: 'When off, this service will not be invoked',
    unitSecond: 's',
    name: 'Service Name',
    namePlaceholder: 'Enter service name',
    transportType: 'Transport Type',
    serviceUrl: 'Service URL',
    serviceUrlPlaceholder: 'https://example.com/mcp',
    enableService: 'Enable Service',
    authConfig: 'Authentication',
    authType: 'Auth Method',
    authTypeNone: 'None / Custom Header',
    authTypeApiKey: 'API Key / Token',
    authTypeOAuth: 'OAuth 2.0 (authorize on first connect)',
    oauthScopes: 'Scopes (optional, space-separated)',
    oauthClientId: 'Client ID (optional)',
    oauthClientIdDesc: 'A client registered with the authorization server in advance. Leave empty to register one automatically (dynamic client registration). When you change the Client ID, update the Client Secret too.',
    oauthClientSecret: 'Client Secret (optional)',
    oauthAuthorization: 'Authorization Status',
    oauthAuthorized: 'Authorized',
    oauthRefreshable: 'Token expired; it will refresh automatically on next use',
    oauthUnauthorized: 'Unauthorized',
    oauthAuthorize: 'Authorize',
    oauthReauthorize: 'Re-authorize',
    oauthRevoke: 'Revoke',
    oauthAuthorizeHint: 'Clicking "Authorize" saves the current config first, then starts authorization (each user authorizes individually).',
    apiKeyHeader: 'Header Name',
    apiKeyHeaderDesc: 'Defaults to X-API-Key. For Bearer, set Authorization and put "Bearer <token>" in the value below; for raw-token services use Authorization with the raw token.',
    credentialValue: 'Secret / Token',
    optional: 'Optional',
    advancedConfig: 'Advanced',
    timeoutSec: 'Timeout (s)',
    rules: {
      nameRequired: 'Please enter the service name',
      transportRequired: 'Please select a transport type',
      urlRequired: 'Please enter the service URL',
      urlInvalid: 'Please enter a valid URL'
    },
    toasts: {
      updated: 'MCP service updated',
      updateFailed: 'Failed to update MCP service',
      authorized: 'Authorization succeeded',
      authorizeFailed: 'Failed to start authorization',
      revoked: 'Authorization revoked',
      revokeFailed: 'Failed to revoke authorization'
    },
    customHeaders: {
      label: 'Custom Headers (optional)',
      desc: 'HTTP headers attached to every MCP request, commonly used for enterprise gateway auth, tracing, etc.',
      add: 'Add Header',
      keyPlaceholder: 'Header name',
      valuePlaceholder: 'Header value'
    },
    codeImport: {
      toggle: 'Import from code',
      hint: 'Paste a standard mcpServers JSON config to auto-fill the form',
      parse: 'Parse & Fill',
      editOverwriteHint: 'Importing overwrites the current form (saved credentials are unaffected; click Save to apply)',
      errors: {
        empty: 'Please paste the config first',
        invalidJson: 'Unable to parse, please check the JSON format',
        noServer: 'No MCP service config found',
        missingUrl: 'The config is missing a url',
        stdioUnsupported: 'stdio (command/args) configs are not supported; please use a remote config with a url'
      },
      toasts: {
        filled: 'Form filled, please review and save',
        multipleServers: 'Multiple services detected, imported the first one: {name}'
      }
    }
  },
  promptTemplate: {
    noTemplates: 'No templates available',
    selectTemplate: 'Select Template',
    useTemplate: 'Use Template',
    resetDefault: 'Reset Default',
    default: 'Default',
    withKnowledgeBase: 'KB',
    withWebSearch: 'Web Search'
  },
  organization: {
    owner: 'Creator',
    join: {
      title: 'Join Shared Space'
    },
    roleUpdated: 'Role updated',
    roleUpdateFailed: 'Failed to update role',
    createdByMe: 'Created by me',
    joinedByMe: 'Joined',
    role: {
      admin: 'Admin',
      editor: 'Editor',
      viewer: 'Viewer'
    },
    settings: {
      pendingJoinRequestsBadge: 'Pending join requests to review'
    },
    share: {
      title: 'Share to Shared Space',
      selectOrg: 'Select Shared Space',
      selectOrgPlaceholder: 'Select a shared space to share with',
      permission: 'Permission',
      permissionTip: 'Editable permission allows members to modify knowledge base content, Read-only permission only allows search and Q&A',
      shareSuccess: 'Knowledge base shared',
      shareFailed: 'Failed to share',
      unshareSuccess: 'Share cancelled',
      unshareFailed: 'Failed to cancel share',
      sharedTo: 'Shared to',
      noShares: 'Not shared to any shared space yet',
      searchPlaceholder: 'Search shared spaces…',
      loading: 'Loading…',
      emptySearch: 'No shared spaces matching "{q}"',
      addShareDialogTitle: 'Share to shared space',
      unshareAction: 'Remove share',
      columns: {
        space: 'Shared Space',
        permission: 'Permission',
        sharedAt: 'Shared',
        operations: 'Actions'
      },
      sharedFrom: 'From',
      permissionReadonly: 'Read-only',
      permissionEditable: 'Editable'
    }
  },
  preview: {
    loading: 'Loading document preview...',
    loadFailed: 'Failed to load document preview',
    retry: 'Retry',
    unsupported: 'This file type does not support online preview',
    unsupportedHint: 'Please download and open with a local application',
    zoomIn: 'Zoom in',
    zoomOut: 'Zoom out',
    fullscreen: 'Fullscreen',
    exitFullscreen: 'Exit Fullscreen',
    htmlRendered: 'Rendered preview',
    htmlSource: 'View source',
    audioNotSupported: 'Your browser does not support audio playback',
    videoNotSupported: 'Your browser does not support video playback'
  },
  assistant: {
    title: 'Xiaozhi Assistant',
    newConversation: 'New conversation',
    history: 'Conversation history',
    untitledConversation: 'Untitled conversation',
    historyEmpty: 'No conversations yet',
    historyFailed: 'Failed to load conversation history',
    loadMore: 'Load more',
    resize: 'Resize assistant',
    layout: {
      dock: 'Dock to the side',
      float: 'Float over the page'
    },
    welcomeTitle: 'How can I help?',
    agentWelcomeDesc: 'Check this agent’s configuration, change its model or see which knowledge bases it can search.',
    welcomeDesc: 'I can answer questions about Xiaozhi, organize knowledge and documents, and help set up agents, tools and automations.',
    help: {
      label: 'About the assistant',
      title: 'What the Xiaozhi assistant can do',
      identity: 'The assistant works as you. It can see and change only what your role in this workspace allows.',
      page: 'It keeps the current page attached, so it can summarize what is on screen, set up agents and automations, or fill in forms. It will not click buttons or save for you.',
      access: 'Under the input you can switch access: read-only, confirm before changes, or run recoverable changes automatically. Deletes always need your confirmation, and an admin ceiling cannot be exceeded.'
    },
    welcomeDescriptions: {
      knowledgeBases: 'I can help choose a knowledge base type, organize your material and find the right sources for your questions.',
      knowledgeBase: 'I can summarize what these documents cover, point out recent updates, and find files that have not finished parsing.',
      document: 'I can summarize this document, turn it into step-by-step instructions or draft FAQs from its content.',
      faq: 'I can check FAQ coverage, find duplicate questions and help make answers clearer.',
      wiki: 'I can summarize this page, trace its sources and help find content that needs expanding or updating.',
      agents: 'Tell me what you want to accomplish. I can help create an agent with the right model, knowledge bases and tools.',
      automation: 'I can turn repeated work into scheduled tasks, review run results and adjust schedules.',
      skills: 'Tell me your task. I can help find and add skills, then enable them for the right agent.',
      mcp: 'I can help find and connect MCP services, explain their tools and configure them for your agents.',
      browser: 'I can guide you through connecting a browser, suitable automation tasks and the permissions they need.',
      model: 'I can help connect models, compare their uses and check whether a configuration suits your task.',
      chat: 'I can summarize what this conversation asked and produced, check the latest answer, and suggest what to ask next.',
      message: 'I can trace this answer’s sources, check key details and help turn it into reusable content.',
      artifacts: 'I can sort these files by time and type, find the conversation each one came from, and explain how to have an agent save its results.',
      organizations: 'I can show what knowledge bases and agents each shared space makes available, and how to create, join or invite people.'
    },
    settingsPages: {
      fallback: {
        description: 'I can explain what this settings page does, what a change affects, and what to configure first.',
        q1: 'What is this settings page for?',
        q2: 'What will change if I edit these options?',
        q3: 'Which settings should I configure first?'
      },
      general: {
        description: 'I can explain language, theme and other personal preferences, and where they apply.',
        q1: 'Which parts of the UI do these preferences affect?',
        q2: 'How do I change the language or theme?',
        q3: 'Which personal settings should I set up first?'
      },
      userprofile: {
        description: 'I can help review and update your account profile, and explain what happens after a change.',
        q1: 'Where do I change my account details?',
        q2: 'How do I change my avatar, name or password?',
        q3: 'Do I need to sign in again after updating my account?'
      },
      assistant: {
        description: 'I can explain the assistant entry points, permission levels, and what it may or may not do for you.',
        q1: 'What does each assistant permission level mean?',
        q2: 'How do I put the assistant in the sidebar or the corner?',
        q3: 'Can the assistant change settings or delete things for me?'
      },
      envvars: {
        description: 'I can explain where these environment variables are used, and how personal values differ from workspace ones.',
        q1: 'Which skills or agents use these environment variables?',
        q2: 'How do I fill in my own secrets safely?',
        q3: 'What is the difference between workspace and personal variables?'
      },
      tenant: {
        description: 'I can show this workspace’s name, quota and basic info, and what you can edit.',
        q1: 'What is this workspace’s name and storage quota?',
        q2: 'How do I change the workspace name or description?',
        q3: 'What happens when storage is almost full?'
      },
      members: {
        description: 'I can list members and roles, explain invites, and what each role can do.',
        q1: 'Who is in this workspace, and what are their roles?',
        q2: 'How do I invite a new member?',
        q3: 'What can an admin do that a regular member cannot?'
      },
      chathistory: {
        description: 'I can tell you whether chat-history search is on, what it can find, and how to build the index.',
        q1: 'Is chat-history search turned on?',
        q2: 'What past conversations can it search after I turn it on?',
        q3: 'How do I index past conversations?'
      },
      ollama: {
        description: 'I can walk you through connecting local Ollama and adding its models to this workspace.',
        q1: 'How do I connect a local Ollama instance?',
        q2: 'How do I add its models to this workspace after connecting?',
        q3: 'What should I check if Ollama will not connect?'
      },
      vectorstore: {
        description: 'I can explain the current vector engine, what changing it does, and how to check it.',
        q1: 'Which vector search engine is in use now?',
        q2: 'Will changing the engine affect existing knowledge bases?',
        q3: 'How do I check that the search engine is working?'
      },
      parser: {
        description: 'I can show the default document parser, which formats need another engine, and what to change after a failure.',
        q1: 'Which document parser is the default?',
        q2: 'Which file formats need a different parser?',
        q3: 'What should I change when document parsing fails?'
      },
      storage: {
        description: 'I can explain where files are stored, how to switch to object storage, and what happens at quota.',
        q1: 'Where are uploaded files stored right now?',
        q2: 'How do I switch to object storage?',
        q3: 'What happens when the storage quota is used up?'
      },
      sandbox: {
        description: 'I can explain what the sandbox runs, how to add a config, and what to check when scripts fail.',
        q1: 'What is the sandbox used for?',
        q2: 'How do I add a sandbox configuration?',
        q3: 'Which sandbox settings should I check when an agent script fails?'
      },
      websearch: {
        description: 'I can show configured web-search providers and how to let agents search the web.',
        q1: 'Which web search services are configured?',
        q2: 'How do I give agents web search?',
        q3: 'Where do I put the search API key?'
      },
      system: {
        description: 'I can tell you the current version, component status, and what to check before an upgrade.',
        q1: 'What version is this, and what changed recently?',
        q2: 'How do I check the status of this deployment’s components?',
        q3: 'What should I review or back up before upgrading?'
      },
      'system-global': {
        description: 'I can walk through this deployment’s global settings, users and workspaces, and security switches.',
        q1: 'Which global settings does this deployment have?',
        q2: 'How do I manage users and workspaces on the platform?',
        q3: 'What do the security switches control?'
      },
      'system-global-access': {
        description: 'I can explain the login, signup and access-control switches.',
        q1: 'What does each access-control switch restrict?',
        q2: 'How do I turn off open signup or limit sign-in methods?',
        q3: 'Do I need to restart the service after changing these?'
      },
      'system-global-users': {
        description: 'I can list platform users, explain roles, and how to disable or adjust an account.',
        q1: 'Which users are on this platform?',
        q2: 'How do I disable a user or change their permissions?',
        q3: 'How is a system admin different from a regular user?'
      },
      'system-global-tenant': {
        description: 'I can explain workspace policy, default quotas, and what a new workspace inherits.',
        q1: 'What defaults apply when someone creates a workspace?',
        q2: 'How do I limit how many workspaces one person can create?',
        q3: 'What is the default storage quota for a workspace?'
      },
      'system-global-runtime': {
        description: 'I can explain how runtime, task and resource options affect background work.',
        q1: 'Which background tasks do these runtime settings affect?',
        q2: 'How do I limit concurrency or timeouts?',
        q3: 'When do runtime changes take effect?'
      },
      'system-global-security': {
        description: 'I can explain security policy, keys and session switches, and the risk of changing them.',
        q1: 'What does each security switch protect?',
        q2: 'How do I rotate or revoke a platform-level key?',
        q3: 'Which security changes affect users who are already signed in?'
      },
      'system-global-other': {
        description: 'I can explain uncategorized global settings and what to watch before changing them.',
        q1: 'What are these uncategorized settings for?',
        q2: 'What does changing one of them affect?',
        q3: 'Which of these should I avoid changing in production?'
      },
      'model-catalog': {
        description: 'I can browse the model catalog and explain how to add a vendor model to this workspace.',
        q1: 'Which vendors and models can I connect from the catalog?',
        q2: 'How do I add a catalog model to this workspace?',
        q3: 'What is still missing before I can use a vendor?'
      },
      'runtime-queues': {
        description: 'I can show stuck task queues and how to retry failed parse or index jobs.',
        q1: 'Which task queues are stuck right now?',
        q2: 'How do I retry a failed parse or index job?',
        q3: 'How do I see the jobs running in a queue?'
      },
      'platform-api-keys': {
        description: 'I can tell platform keys from workspace keys, and how to create or revoke them.',
        q1: 'What is the difference between a platform API key and a workspace key?',
        q2: 'How do I create a key that can only access one workspace?',
        q3: 'How do I revoke a leaked key immediately?'
      },
      'system-audit-log': {
        description: 'I can filter audit events, find risky actions, and say how long logs are kept.',
        q1: 'What high-risk actions happened recently?',
        q2: 'How do I filter audit records by person or workspace?',
        q3: 'How long are these logs kept?'
      },
      'integration-im': {
        description: 'I can walk you through connecting Feishu or WeCom, and what to check when the bot is silent.',
        q1: 'How do I connect Feishu or WeCom to this workspace?',
        q2: 'How do people use an agent from the IM chat?',
        q3: 'What should I check if the bot is not receiving messages?'
      },
      'integration-embed': {
        description: 'I can explain how to embed the chat widget, and which knowledge bases visitors can use.',
        q1: 'How do I embed the chat widget on my website?',
        q2: 'Which knowledge bases or agents can visitors use?',
        q3: 'Which parameters do I need to change in the embed code?'
      },
      'integration-api': {
        description: 'I can explain how to start a chat over the API, which auth to send, and show an example.',
        q1: 'How do I start a conversation through the API?',
        q2: 'What authentication does a request need?',
        q3: 'Is there a ready-made request example?'
      },
      'integration-mcpserver': {
        description: 'I can explain how to expose Xiaozhi as an MCP server, and which tools it offers.',
        q1: 'How do I offer Xiaozhi as an MCP server?',
        q2: 'How does an external client connect?',
        q3: 'Which tools does this server expose?'
      },
      'integration-cli': {
        description: 'I can walk you through installing and signing in to the CLI, and the common commands.',
        q1: 'How do I install and sign in to the WeKnora CLI?',
        q2: 'What knowledge-base and chat operations can the CLI do?',
        q3: 'What are the most useful commands?'
      },
      'integration-chrome': {
        description: 'I can explain what the browser extension does, how to install it, and where selected text goes.',
        q1: 'What can the browser extension do?',
        q2: 'How do I install and sign in to the extension?',
        q3: 'Where does text I select in the extension get sent?'
      },
      'integration-claw': {
        description: 'I can explain how to connect Xiaozhi to Claw, and which skill to install.',
        q1: 'How do I connect Xiaozhi to Claw?',
        q2: 'Which skill do I need to install?',
        q3: 'What can I do in Claw after it is connected?'
      },
      mymemory: {
        description: 'I can show your personal memories, where they are used, and how to add or delete them.',
        q1: 'Which personal memories are saved here?',
        q2: 'How do I add or delete a memory?',
        q3: 'Which conversations use these memories?'
      },
      memory: {
        description: 'I can tell workspace memory apart from personal memory, and how to keep workspace conventions.',
        q1: 'How is workspace memory different from my personal memory?',
        q2: 'Which memory rules are enabled now?',
        q3: 'How do I make agents remember this workspace’s conventions?'
      }
    },
    startFailed: 'Failed to start the assistant. Please try again.',
    chooseAction: 'Choose an action, or describe what you need.',
    create: {
      agentTitle: 'Describe your agent',
      agentAction: 'Create with assistant',
      agentHint: 'Describe who it serves and what it should do. The assistant will choose resources and create it.',
      agentPlaceholder: 'For example: a support agent that answers product questions using our knowledge base, cites sources and acknowledges missing information.',
      automationTitle: 'Create a task with the assistant',
      automationHint: 'Describe what to do and when to run it. The assistant will turn it into an automation.',
      automationPlaceholder: 'For example: every Friday at 5 PM, summarize this week’s updates to the product knowledge base.',
      requestLabel: 'Task description',
      manual: 'Configure manually',
      start: 'Continue with assistant'
    },
    actions: {
      summarizeActivity: 'Summarize these {count} updates',
      toolExamples: 'Show tool examples',
      answerToDocument: 'Turn into a document',
      answerToFaq: 'Save as FAQ',
      answerToAutomation: 'Make a scheduled task',
      writePrompt: 'Help me write',
      refinePrompt: 'Improve prompt',
      diagnose: 'Diagnose',
      refineRules: 'Refine rules',
      analyzeChunks: 'Analyze chunks'
    },
    prompts: {
      createAgent: 'Create an agent for this request: {request}. Check available models, knowledge bases, MCP services and skills; choose suitable resources. Ask only for necessary missing information, follow the current access policy, and open its editor after creation.',
      createAutomation: 'Create a scheduled task: {request}. Use timezone {timezone} unless specified otherwise. Write self-contained instructions, validate the schedule and show upcoming run times. Follow current access rules without increasing execution permissions, then open the created task.',
      summarizeActivity: 'Summarize only loaded_entry_ids in this filter snapshot: {scope}. Query with these filters and paginate as needed. Describe affected resources, actors and outcomes. Distinguish audit events from content changes; loaded records are not all activity.',
      explainMcpTools: 'Read the saved tool directory for MCP service {id}. Explain its capabilities with three useful example requests and note stale or incomplete metadata. Do not refresh, call tools or change configuration.',
      answerToDocument: 'Read this answer and its question: {source}. Draft a structured document preserving citations and uncertainty. Show it and ask for the destination knowledge base, then create it under current access rules without overwriting existing content.',
      answerToFaq: 'Read this answer and its question: {source}. Draft a standard question and accurate answer. Show the draft, ask for a destination FAQ knowledge base and check similar entries before saving under current access rules. Do not overwrite entries.',
      answerToAutomation: 'Read this answer and its question: {source}. Turn the repeatable work into a self-contained scheduled task. Ask for missing frequency, time or timezone; validate and show upcoming runs before creating under current access rules. Do not raise execution permissions.',
      writePrompt: 'Help me draft a system prompt based on the purpose and configuration of the current agent. Ask me first if the goal is unclear. Fill the current editor with your suggestion, preserving template placeholders. Do not save or change the saved agent.',
      refinePrompt: 'Improve the attached system prompt to clarify responsibilities, response requirements, and tool usage rules. Preserve its intent and template placeholders. Fill the current editor with the revision without saving or changing the saved agent.',
      modelFailure: 'Analyze the attached connection error using the current model configuration and suggest troubleshooting steps. Do not read or display credentials, and do not change or save the configuration.',
      mcpFailure: 'Inspect the MCP service (ID: {id}) and diagnose the attached tool discovery or synchronization error. Suggest troubleshooting steps without reading or revealing credentials, reconnecting, or changing the configuration.',
      syncFailure: 'Inspect sync log {log} for data source "{source}" (ID: {id}). Use the attached error samples and failure counts to explain the cause and suggest next steps. Do not retry the sync or modify the data source.',
      writeWikiRules: 'Draft clear rules for "{field}" based on the purpose of the current knowledge base. Ask me first if the purpose is unclear. Fill the corresponding editor field, preserving the system citation and output protocols. Do not save or reparse.',
      refineWikiRules: 'Clarify the attached "{field}" rules while preserving their meaning. Fill the corresponding editor field, preserving the system citation and output protocols. Do not save or reparse.',
      analyzeChunks: 'Analyze this attached chunking preview using its original-text and chunk excerpts, the parameters used for that run, and the statistics. Identify fragmented meaning or overly short or long chunks, and suggest parameter changes. Distinguish findings supported by the excerpts from those needing more source text. Do not change settings or rebuild the knowledge base.'
    },
    askAboutAnswer: 'Ask {name} about this answer',
    selection: {
      label: 'Selected',
      lines: '{count} lines selected',
      detach: 'Don’t include the selection',
      tip: 'Your selection goes with the message: {text}',
      tipField: 'Your selection in “{field}” goes with the message: {text}'
    },
    bubble: {
      label: 'Assistant actions',
      ask: 'Ask assistant',
      polish: 'Polish',
      rewrite: 'Rewrite',
      translate: 'Translate',
      continue: 'Continue',
      prompts: {
        polish: 'Polish the selected text: fix typos and awkward phrasing without changing the meaning, and replace it in place.',
        rewrite: 'Rewrite the selected text to be clearer and more concise, and replace it in place.',
        translate: 'Translate the selected text, Chinese into English and other languages into Chinese, and replace it in place.',
        continue: 'Continue writing after the selected text with one more paragraph that fits the context, placed right after it.'
      }
    },
    fillNotice: {
      title: 'Assistant filled {count} field(s)',
      undo: 'Undo',
      dismiss: 'Dismiss'
    },
    access: {
      title: 'Access level',
      capped: 'Not allowed by your workspace admin',
      page: {
        label: 'See and fill the current page',
        desc: 'Reads the page on the left and can fill in forms. Never clicks buttons or saves.'
      },
      levels: {
        read_only: {
          label: 'Read only',
          desc: 'Looks, never changes anything'
        },
        confirm: {
          label: 'Ask first',
          desc: 'Asks you before every change or deletion'
        },
        auto_write: {
          label: 'Auto',
          desc: 'Makes recoverable changes directly; still asks before deleting'
        }
      }
    },
    context: {
      currentPage: 'Current page',
      detach: 'Don\'t include the current page',
      attachedTip: 'Including the current page: {path}',
      detachedTip: 'Click to include the current page: {path}',
      chatMessage: 'This answer',
      pages: {
        knowledge_base: 'Knowledge base',
        wiki: 'Wiki',
        agent_editor: 'Agent editor',
        settings_models: 'Models',
        mcp_services: 'MCP services',
        settings: 'Settings',
        chat: 'Chat'
      }
    },
    starters: {
      agentConfig: 'How could this agent’s configuration be improved?',
      agentModel: 'Which model would be a better fit for this agent?',
      agentKnowledge: 'Which knowledge bases can it search?',
      wikiIssues: 'What needs to be added or verified on this Wiki page?',
      wikiSummary: 'What are the main points of this Wiki page?',
      documentSummary: 'What are this document’s key conclusions?',
      recentActivity: 'Which documents were uploaded or updated recently?',
      agents: 'What kinds of questions is each of these agents good at?',
      messageSources: 'What is this answer based on?',
      messageCheck: 'Is anything in this answer wrong?',
      modelCheck: 'Is this model configured well for its current use?',
      modelUsage: 'Which agents and knowledge bases use these models?',
      mcpTools: 'Which tools does this MCP service offer?',
      mcpCheck: 'What else needs configuring before I use this service?',
      modelSetup: 'Which models do I still need to set up?',
      mcpSetup: 'How do I connect an MCP service?',
      releaseHighlights: 'What are the main changes in the current version?',
      gettingStarted: 'What should I set up first in Xiaozhi?',
      workflow: 'How do knowledge bases, agents and automations work together?',
      knowledgeOverview: 'What can I find in each of these knowledge bases?',
      knowledgeType: 'When should I use documents, FAQ or Wiki?',
      knowledgeOrganize: 'How should I organize my materials into a useful knowledge base?',
      knowledgeTopics: 'What does each of these documents cover?',
      knowledgeGaps: 'Which documents failed to parse or are still processing?',
      faqCoverage: 'Which common questions do these FAQs cover?',
      faqDuplicates: 'Which FAQs overlap and could be merged?',
      faqImprove: 'Which answers need more detail or an update?',
      documentSteps: 'Turn the steps in this document into instructions I can follow',
      documentFaq: 'Which FAQs could we extract from this document?',
      wikiSources: 'Which sources support this Wiki page’s conclusions?',
      agentCreate: 'How do I create an agent that answers from a knowledge base?',
      agentChoose: 'Which of these agents should I use to search a knowledge base?',
      automationIdeas: 'Which repetitive tasks could I automate?',
      automationCreate: 'Set up a weekly summary of knowledge base updates',
      automationOverview: 'How have my automations been running recently?',
      automationSummary: 'What did this task produce in its latest run?',
      automationSchedule: 'When will this task run next?',
      automationImprove: 'How could I improve this task’s prompt and schedule?',
      skillFind: 'Which of these skills are worth adding to an agent?',
      skillAdd: 'How do I add a new skill and enable it for an agent?',
      skillUse: 'What can each of the added skills do?',
      mcpFind: 'Which tools from these MCP services can an agent call?',
      mcpExamples: 'How do I let an agent use these MCP tools?',
      mcpUsage: 'Show an example of how to use this service’s tools',
      modelFit: 'Which tasks is this model best suited for?',
      modelTypes: 'How should I choose chat, embedding and reranking models?',
      browserConnect: 'How do I connect a browser for an agent to use?',
      browserTasks: 'Which web tasks can the browser automate?',
      browserReconnect: 'How do I reconnect when the browser shows as offline?',
      messageReuse: 'Turn this answer into steps I can follow',
      chatSummary: 'What was asked in this conversation, and what came out of it?',
      chatCheck: 'Did the latest answer miss or get anything wrong?',
      chatFollowup: 'Based on this conversation, what else can I ask next?',
      artifactRecent: 'Which files were generated recently?',
      artifactSources: 'Which conversation did each of these files come from?',
      artifactCreate: 'How do I have an agent save its results as files?',
      organizationShared: 'What knowledge bases and agents does each shared space provide?',
      organizationJoin: 'How do I join an existing shared space?',
      organizationCreate: 'How do I create a shared space and invite members?'
    }
  },
  commandPalette: {
    placeholder: 'Search knowledge bases, files, conversations…',
    clearRecent: 'Clear',
    retrieval: 'Retrieval settings',
    untitledSession: 'Untitled conversation',
    scope: {
      placeholder: 'Search within this knowledge base…',
      remove: 'Remove scope (Backspace)'
    },
    group: {
      chunks: 'Files',
      messages: 'Messages',
      kbs: 'Knowledge bases',
      agents: 'Agents',
      sessionsByTitle: 'Chats (by title)',
      commands: 'Commands',
      recent: 'Recent',
      quickActions: 'Quick actions'
    },
    match: {
      vector: 'Vector',
      keyword: 'Keyword'
    },
    quick: {
      newChat: 'New conversation',
      knowledgeBases: 'Open knowledge bases',
      agents: 'Open agents',
      organizations: 'Open shared spaces',
      settings: 'Open settings',
      productTour: 'Product tour',
      assistant: 'Open {name}'
    },
    empty: {
      noResults: 'No matches found',
      askAi: 'Ask the AI directly',
      adjustRetrieval: 'Adjust retrieval'
    },
    hotkey: {
      select: 'Navigate',
      enter: 'Open',
      cmdNumber: 'Jump to',
      cmdEnter: 'Start chat',
      esc: 'Close'
    }
  },
  tools: {
    multiKbSearch: 'Cross-KB Search',
    searchKnowledge: 'Search knowledge',
    readDocument: 'Read document',
    listDocuments: 'List documents',
    knowledgeSearch: 'Knowledge Search',
    grepChunks: 'Text Pattern Search',
    getChunkDetail: 'Get Chunk Detail',
    listKnowledgeChunks: 'List Knowledge Chunks',
    listKnowledgeBases: 'List Knowledge Bases',
    getDocumentInfo: 'Get Document Info',
    queryKnowledgeGraph: 'Query Knowledge Graph',
    think: 'Deep Thinking',
    todoWrite: 'Make Plan'
  },
  vectorStoreBadge: {
    systemDefault: 'System default',
    sharedFromOrg: 'Shared from another organization',
    unknownStore: 'Unknown store',
    unavailable: 'Unavailable'
  },
  kbSettings: {
    vectorStore: {
      title: 'Vector Store',
      description: 'Choose which vector store this knowledge base writes to. The binding is permanent — to move an existing KB to a different store, create a new KB and re-index.',
      loading: 'Loading vector stores...',
      engineLabel: 'Vector store',
      engineDesc: 'Pick a store from the global Vector Stores configuration, or leave as System default to use the workspace-wide RETRIEVE_DRIVER engine.',
      boundLabel: 'Bound vector store',
      systemDefault: 'System default',
      immutableHint: 'Cannot be changed after creation. To migrate later, create a new KB bound to the desired store and re-index.',
      immutableEdit: 'Vector store binding cannot be changed after creation.',
      unavailableHint: 'The bound vector store is currently unavailable; check its connection configuration in Settings → Vector Stores.',
      goGlobalSettings: 'Go to Vector Store Settings'
    },
    storage: {
      title: 'Storage Engine',
      selectDescription: 'Select the specific storage instance to bind this knowledge base to.',
      defaultTag: 'Default',
      instanceLabel: 'Storage instance',
      instanceDesc: 'The same storage type can have multiple instances with different endpoints, buckets, or credentials.',
      migrateHint: 'This knowledge base already contains files; use the storage migration flow to switch instances.',
      manageInstances: 'Manage storage instances',
      localStorage: 'Local storage',
      loading: 'Loading...'
    },
    parser: {
      title: 'Parser Engine',
      description: 'Select document parser engines for different file types. Unconfigured file types will use the built-in parser.',
      loading: 'Loading...',
      noEngineAvailable: 'No parser engine available, or the document parsing service is not configured.',
      default: 'Default',
      goConfig: 'Go to Config →',
      noEngine: 'No available engine',
      fileTypePdf: 'PDF Documents',
      fileTypeWord: 'Word Documents',
      fileTypePpt: 'Presentations',
      fileTypeExcel: 'Excel Spreadsheets',
      xlsxFirstRowAsHeader: 'Use the first row as column context for every row',
      fileTypeEbook: 'E-books',
      fileTypeWebArchive: 'Web Archives',
      fileTypeCsv: 'CSV Files',
      fileTypeText: 'Plain Text',
      fileTypeJson: 'JSON Files',
      fileTypeImage: 'Images',
      fileTypeAudiovisual: 'Audio',
      engines: {
        builtin: {
          name: 'Built-in',
          desc: 'DocReader built-in parser engine (docx/pdf/xlsx and other complex formats)'
        },
        simple: {
          name: 'Simple',
          desc: 'Simple format & image parsing (no external service required)'
        },
        anydoc: {
          name: 'anydoc',
          desc: 'In-process office document parser (no external service required)'
        },
        mineru: {
          name: 'MinerU',
          desc: 'MinerU self-hosted service'
        },
        mineru_cloud: {
          name: 'MinerU Cloud',
          desc: 'MinerU Cloud API'
        },
        paddleocr_vl: {
          name: 'PaddleOCR-VL',
          desc: 'PaddleOCR-VL self-hosted service'
        },
        paddleocr_vl_cloud: {
          name: 'PaddleOCR-VL Cloud',
          desc: 'PaddleOCR-VL Cloud API'
        },
        markitdown: {
          name: 'MarkItDown',
          desc: 'Microsoft MarkItDown converter (PDF/Office/HTML and more)'
        },
        opendataloader: {
          name: 'OpenDataLoader',
          desc: 'OpenDataLoader PDF parser (layout analysis; requires Java 11+ and opendataloader-pdf)'
        }
      }
    }
  },
  agentStream: {
    askUser: {
      answerLabel: 'Your answer',
      title: 'Question for you',
      selectPlaceholder: 'Select',
      textPlaceholder: 'Type your answer',
      otherPlaceholder: 'Other (optional)',
      decline: 'Skip',
      submit: 'Submit',
      declinedTag: 'Declined to answer',
      submitted: 'Submitted',
      answeredTag: 'Answered',
      timedOutTag: 'No answer in time',
      canceledTag: 'Canceled',
      unansweredTag: 'Not answered',
      submitFailed: 'Failed to submit'
    },
    secureForm: {
      onlyFillInto: 'Only filled into: {domains}',
      observedAt: 'Browser is on: {origin}',
      originUnknown: 'Could not confirm the page the browser is on. Make sure it shows the site you are signing in to.',
      originMismatch: 'The browser is on {origin}, not the site you are signing in to. Check before filling.',
      originInsecure: 'The browser page is not HTTPS; credentials will not be filled there.',
      savedAccount: 'Saved account',
      useNew: 'Use a new username and password',
      username: 'Username',
      password: 'Password',
      saveToVault: 'Save to vault',
      useOnce: 'Use once',
      fill: 'Fill in',
      decline: 'Decline',
      submittedHidden: 'Submitted (contents hidden)',
      declined: 'Declined',
      timedOut: 'Timed out',
      canceled: 'Canceled',
      submitFailed: 'Submission failed',
      savedButClosed: 'The credential was saved to your vault, but this request has already ended'
    },
    promptDock: {
      approvalTitle: 'Needs your review',
      oauthTitle: 'Needs your authorization',
      secureFormTitle: 'Needs your credentials',
      waiting: 'Waiting for you',
      handle: 'Respond',
      pager: '{current} / {total}',
      previous: 'Previous',
      next: 'Next',
      collapse: 'Collapse',
      expand: 'Expand'
    },
    toolApproval: {
      title: 'Approval',
      toolDescription: 'Tool description',
      delegatedTask: 'Delegated task',
      waitingStatus: 'Awaiting review',
      targetWithTool: '{service} › {tool}',
      dockQuestion: 'Allow {target} to run?',
      operationQuestion: 'Allow {action}: “{target}”?',
      operationQuestionNoTarget: 'Allow {action}?',
      operationTarget: '{action}: “{target}”',
      characterCount: '{count} characters',
      argsLabel: 'Arguments',
      argsModified: 'Modified',
      allowInSession: 'Allow this for the rest of the conversation',
      grantLapsed: {
        changed: 'Your earlier approval no longer applies: the automation\'s agent setup, your role or the access ceiling changed.',
        expired: 'Your earlier approval has expired.',
        idle: 'Your earlier approval lapsed after a long time unused.'
      },
      countdownShort: '{seconds}s',
      approve: 'Approve & run',
      reject: 'Reject',
      approvedTag: 'Approved',
      rejectedTag: 'Rejected',
      parked: 'Waiting in the background — answer any time',
      parkedUntil: 'Waiting in the background — answer before {time}',
      abandonedTag: 'Abandoned',
      canceledTag: 'Canceled',
      invalidJson: 'Arguments must be valid JSON',
      submitted: 'Submitted',
      submitFailed: 'Submit failed',
      userRejected: 'User rejected',
      detail: {
        type: 'Type',
        embeddingModel: 'Embedding model',
        summaryModel: 'Summary model',
        captionModel: 'Caption model',
        speechModel: 'Speech model',
        storage: 'Storage',
        indexes: 'Indexes',
        name: 'Name',
        title: 'Title',
        status: 'Status',
        summary: 'Summary',
        model: 'Model',
        mode: 'Mode',
        url: 'URL',
        from: 'From',
        to: 'To',
        folder: 'Folder',
        page: 'Page',
        version: 'Version',
        documents: 'Documents',
        knowledgeBases: 'Knowledge bases',
        mcpServices: 'MCP services',
        skills: 'Skills',
        webSearch: 'Web search',
        multiTurn: 'Multi-turn conversation',
        transport: 'Transport',
        authentication: 'Authentication',
        usageInstructions: 'Usage instructions',
        displayName: 'Display name',
        enabled: 'Enabled',
        sandbox: 'Sandbox',
        sandboxes: 'Sandboxes',
        systemPrompt: 'System prompt',
        content: 'Content',
        kbScope: 'Knowledge base scope',
        mcpScope: 'MCP scope',
        skillsScope: 'Skills scope'
      },
      value: {
        document: 'Document',
        faq: 'FAQ',
        wiki: 'Wiki',
        on: 'On',
        off: 'Off',
        vector: 'Vector',
        keyword: 'Keyword',
        graph: 'Graph',
        quickAnswer: 'Quick answer',
        smartReasoning: 'Smart reasoning',
        indexSep: ', '
      }
    },
    hostApproval: {
      command: 'Command',
      grantPath: 'Needs access to',
      accessWrite: 'Read and write',
      accessRead: 'Read only',
      firstAttemptRan: 'This command already ran once and failed. Approving runs the whole command again.',
      snippet: 'Block details',
      sessionRules: 'If allowed for this session, these deletes in this directory are not asked again (file names may differ)',
      reject: 'Reject',
      approveOnce: 'Allow once',
      approveSession: 'Allow for this session',
      approvedOnce: 'Allowed once',
      approvedSession: 'Allowed for this session',
      rejectedTag: 'Rejected',
      submitted: 'Submitted',
      submitFailed: 'Submission failed',
      userRejected: 'Rejected by user',
      fileOnly: 'Only this file is opened',
      writeMode: 'Mode',
      writeModeOverwrite: 'Overwrite',
      writeModeAppend: 'Append',
      writeModeEdit: 'Edit',
      writeBytes: '{bytes} bytes',
      preview: 'Content',
      previewTruncated: 'Showing the first 64 KB',
      env: 'Environment variables',
      skillName: 'Skill',
      stdin: 'Standard input',
      script: 'Script this command runs'
    },
    hostReview: {
      denied: 'Auto review denied: {reason}'
    },
    mcpOAuth: {
      waiting: 'Awaiting authorization · {target}',
      waitingStatus: 'Awaiting authorization',
      targetWithTool: '{service} › {tool}',
      dockQuestion: 'Authorize {target} to continue',
      titleWithService: 'OAuth · {service}',
      titleWithTool: 'OAuth · {service} › {tool}',
      desc: 'Authorizing opens a new window to sign in. The tool call resumes automatically once authorization succeeds.',
      authorize: 'Authorize',
      skip: 'Skip',
      countdownShort: '{seconds}s',
      authorizedTag: 'Authorized',
      timedOutTag: 'Authorization timed out',
      canceledTag: 'Canceled',
      authorizedToast: 'Authorized. Resuming…',
      startFailed: 'Failed to start authorization',
      resumeFailed: 'Failed to resume. Please try again.',
      skipFailed: 'Failed to skip. Please try again.'
    },
    tools: {
      searchKnowledge: 'Knowledge Search',
      grepChunks: 'Text Pattern Search',
      webSearch: 'Web Search',
      webFetch: 'Web Fetch',
      getDocumentInfo: 'Get Document Info',
      listKnowledgeChunks: 'List Knowledge Chunks',
      getRelatedDocuments: 'Find Related Documents',
      getDocumentContent: 'Get Document Content',
      wikiReadSourceDoc: 'Deep-read Source Doc',
      readDocument: 'Read document',
      listDocuments: 'List documents',
      todoWrite: 'Plan Management',
      askUser: 'Ask User',
      requestSecureForm: 'Request credentials',
      browserFillSecret: 'Fill credentials',
      knowledgeGraphExtract: 'Knowledge Graph Extraction',
      thinking: 'Thinking',
      attachmentParsing: 'Parsing Attachment',
      imageAnalysis: 'Image Analysis',
      queryUnderstand: 'Understand Query',
      queryKnowledgeGraph: 'Knowledge Graph Query',
      readSkill: 'Read Skill',
      executeSkillScript: 'Execute Skill Script',
      listSandboxFiles: 'List sandbox files',
      readFile: 'Read file',
      readSandboxFile: 'Read sandbox file',
      writeSandboxFile: 'Write sandbox file',
      editSandboxFile: 'Edit sandbox file',
      shellExec: 'Run sandbox command',
      dataAnalysis: 'Data Analysis',
      dataSchema: 'Data Schema',
      databaseQuery: 'Database Query',
      findOperations: 'Find operations',
      runOperation: 'Run operation',
      spawn_agent: 'Start agent',
      list_agents: 'List agents',
      send_message: 'Send message',
      followup_task: 'Continue task',
      interrupt_agent: 'Interrupt agent',
      wait_agent: 'Wait for agent',
      openPage: 'Open page',
      viewPage: 'View page',
      searchWeKnoraDocs: 'Search product docs',
      readWeKnoraDoc: 'Read product doc',
      readPage: 'View page',
      selectTab: 'Select tab',
      fillPage: 'Fill page'
    },
    collaboration: {
      tabs: 'Task tabs',
      updates: '{count} updates',
      mainConversation: 'Main chat',
      assignment: 'Task brief',
      title: 'Tasks',
      unnamed: 'Unnamed task',
      status: {
        queued: 'Queued',
        running: 'Running',
        waiting: 'Waiting for your input',
        succeeded: 'Completed',
        failed: 'Failed',
        interrupted: 'Interrupted',
        cancelled: 'Cancelled',
        needs_attention: 'Needs attention',
        cancelling: 'Cancelling',
        unknown: 'Unknown status'
      },
      phase: {
        tool_running: 'Using tool',
        tool_succeeded: 'Tool completed',
        tool_failed: 'Tool failed'
      }
    },
    pageAccess: {
      viewed: 'Viewed the current page: {location}'
    },
    pageEdit: {
      title: 'Filled {count} field(s)',
      undo: 'Undo',
      undone: 'Fill undone',
      undoSkipped: '{count} field(s) changed since or no longer on the page were left as they are',
      unsaved: 'Nothing is saved yet. Review it and save on the page.'
    },
    openPage: {
      open: 'Open',
      retired: 'Discontinued',
      openForm: 'Open and fill in',
      opened: 'Opened by the assistant',
      back: 'Back',
      endpoint: 'Connects to: ',
      draftHint: 'Filled in from the assistant. Add the API key or other credentials, check it and save it yourself.'
    },
    skillFiles: {
      heading: 'Skill files',
      script: 'script',
      instructions: 'Instructions'
    },
    attachmentTarget: {
      list: 'all attachments',
      file: 'attachment',
      images: 'images in {name}',
      imagesUnnamed: 'attachment images',
      image: 'image {n} of {name}',
      imageUnnamed: 'attachment image {n}'
    },
    imageView: {
      summary: 'Viewed image {numbers} of {total} in "{file}"',
      single: 'Viewed image "{file}"',
      descriptionsHeading: 'Descriptions from the vision model',
      imageLabel: 'Image #{n}',
      noDescription: 'Could not be described',
      remaining: '{count} more not viewed'
    },
    sandboxFiles: {
      found: 'Found {count} file(s)',
      empty: 'No files',
      truncated: 'List truncated',
      wrote: 'Wrote',
      replacements: 'Replaced {count}',
      moreLines: '{count} more lines'
    },
    shellExec: {
      workDir: 'Directory',
      exitCode: 'Exit code',
      stdout: 'Stdout',
      stderr: 'Stderr',
      emptyOutput: 'No output',
      truncated: 'Output truncated',
      killed: 'Timed out',
      binarySuppressed: 'Binary output omitted. Write files to the artifact directory to download them.'
    },
    operations: {
      names: {
        data_source: {
          list: 'List data sources',
          get: 'Get data source details',
          test: 'Test data source connection',
          sync: 'Sync data source',
          pause: 'Pause data source sync',
          resume: 'Resume data source sync',
          list_sync_logs: 'List data source sync logs',
          get_sync_log: 'Get data source sync progress',
          list_resources: 'List syncable data source resources',
          update_sync: 'Update data source sync settings'
        },
        agent: {
          list: 'List agents',
          create: 'Create agent',
          get: 'Get agent details',
          delete: 'Delete agent',
          update: 'Update agent',
          copy: 'Copy agent'
        },
        artifact: {
          list: 'List generated files'
        },
        chunk: {
          get: 'Get chunk details',
          update: 'Update chunk',
          list_revisions: 'List chunk revisions',
          revert: 'Restore chunk revision',
          list: 'List knowledge chunks'
        },
        knowledge_base: {
          list_parser_engines: 'List available parser engines',
          copy: 'Copy knowledge base content',
          duplicate: 'Copy knowledge base settings',
          get_copy_progress: 'Get knowledge base copy progress',
          list: 'List knowledge bases',
          create: 'Create knowledge base',
          get: 'Get knowledge base details',
          delete: 'Delete knowledge base',
          update: 'Update knowledge base',
          list_activity: 'List knowledge base activity',
          search: 'Search knowledge base',
          list_move_targets: 'List destination knowledge bases',
          generate_profile: 'Generate knowledge base description',
          list_tags: 'List knowledge base tags',
          create_tag: 'Create knowledge base tag',
          update_tag: 'Update knowledge base tag',
          delete_tag: 'Delete knowledge base tag',
          list_shared: 'List shared knowledge bases'
        },
        faq: {
          batch_update: 'Batch update FAQ states and tags',
          list_entries: 'List FAQ entries',
          delete_entries: 'Delete FAQ entries',
          get_entry: 'Get FAQ entry details',
          update_entry: 'Update FAQ entry',
          add_similar_questions: 'Add similar questions',
          create_entry: 'Create FAQ entry'
        },
        knowledge: {
          list: 'List knowledge',
          list_folders: 'List knowledge folders',
          rename_folder: 'Rename or move folder',
          create_manual: 'Create knowledge manually',
          create_from_url: 'Create knowledge from URL',
          batch_delete: 'Delete knowledge in batch',
          batch_reparse: 'Reparse knowledge in batch',
          move_to_folder: 'Move knowledge to folder',
          update_manual: 'Update manually created knowledge',
          move: 'Move knowledge to another knowledge base',
          get_move_progress: 'Get knowledge move progress',
          set_tags: 'Set knowledge tags',
          get: 'Get knowledge details',
          update: 'Update knowledge',
          delete: 'Delete knowledge',
          cancel_parse: 'Cancel knowledge parsing',
          reparse: 'Reparse knowledge',
          get_parse_progress: 'Get knowledge parsing progress'
        },
        wiki: {
          list_folders: 'List Wiki folders',
          create_folder: 'Create Wiki folder',
          list_issues: 'List Wiki page issues',
          lint: 'Check Wiki pages',
          move_page: 'Move Wiki page',
          get_page: 'Get Wiki page',
          rebuild_links: 'Rebuild Wiki links',
          revert: 'Revert Wiki page revision',
          list_revisions: 'List Wiki page revisions',
          get_stats: 'Get Wiki statistics'
        },
        system_admin: {
          list_admins: 'List system administrators',
          list_users: 'List platform users',
          list_settings: 'Read system settings',
          get_queues: 'Read runtime queue status',
          list_tasks: 'List queue tasks'
        },
        workspace: {
          get: 'Get current workspace information',
          update: 'Update current workspace profile',
          list_members: 'List current workspace members'
        },
        system: {
          get_info: 'Get version and system information'
        },
        web_search_provider: {
          list: 'List web search providers',
          get: 'Get web search provider',
          list_types: 'List web search provider types',
          test: 'Test web search connection',
          update: 'Update web search provider',
          delete: 'Delete web search provider'
        },
        mcp_service: {
          list: 'List MCP services',
          create: 'Create MCP service',
          get: 'Get MCP service details',
          update: 'Update MCP service',
          delete: 'Delete MCP service',
          test: 'Test MCP service connection',
          list_tools: 'Query live MCP tools',
          get_metadata: 'View synced MCP tools',
          refresh_metadata: 'Sync MCP tool directory'
        },
        message: {
          chat_history_stats: 'Get chat history statistics',
          search: 'Search conversation history',
          list: 'Get message history'
        },
        model: {
          list: 'List models',
          list_providers: 'List model providers',
          get_provider: 'Get model provider details',
          get: 'Get model details',
          delete: 'Delete model',
          update: 'Update model display information',
          copy: 'Copy model configuration'
        },
        skill: {
          list_installed: 'List installed skills',
          install: 'Install skill',
          get_installed: 'Get installed skill details',
          uninstall: 'Uninstall skill',
          set_enabled: 'Set skill enabled state',
          list: 'List executable skills',
          list_catalog: 'List workspace skills',
          get_catalog: 'Get workspace skill details',
          install_catalog: 'Install catalog skill onto sandboxes'
        },
        automation: {
          list: 'List automations',
          create: 'Create automation',
          validate_trigger: 'Check schedule',
          get: 'Get automation',
          update: 'Update automation',
          delete: 'Delete automation',
          pause: 'Pause automation',
          resume: 'Resume automation',
          run_now: 'Run automation now',
          list_runs: 'List automation runs'
        },
        session: {
          list: 'List conversations'
        }
      },
      found: '{count} available',
      unavailableCount: '{count} unavailable',
      empty: 'No matching operations',
      unavailableHeading: 'Unavailable',
      parameters: 'Parameters',
      required: 'Required',
      enum: 'Values',
      range: 'Range {min}–{max}',
      risk: {
        read: 'Read',
        probe: 'Check',
        write: 'Write',
        destructive: 'Destructive'
      },
      truncated: 'Result truncated',
      emptyResult: 'No data returned',
      failed: 'Operation failed',
      meta: 'Details'
    },
    weknoraDocs: {
      pages: '{count} pages',
      hits: '{count} matching sections',
      empty: 'No matching documentation',
      outline: 'Outline',
      content: 'Content',
      truncated: 'The page continues',
      failed: 'Could not read the page',
      openDoc: 'Open in docs'
    },
    citation: {
      notFound: 'Content not found',
      loadFailed: 'Failed to load',
      noKbForWiki: 'Unable to identify associated knowledge base. Cannot open Wiki.'
    },
    entityLink: {
      kb: 'Knowledge base',
      doc: 'Document',
      chunk: 'Passage'
    },
    toolSummary: {
      getDocument: 'Get document: {title}',
      document: 'Document',
      listChunks: 'View {title}',
      listFaqEntry: 'View FAQ: {question}',
      deepThinking: 'Deep Thinking'
    },
    plan: {
      inProgress: 'In Progress',
      pending: 'Pending',
      completed: 'Completed'
    },
    search: {
      noResults: 'No matching content found',
      candidatesBelowThreshold: 'Matched {count} candidate(s), none relevant enough to use',
      foundResultsFromFiles: 'Found {count} result(s) from {files} file(s)',
      foundResults: 'Found {count} result(s)',
      foundMixedResults: 'Found {count} result(s) ({docCount} documents, {webCount} web results)',
      webResults: 'Found {count} web result(s)',
      grepSummary: 'Found {chunks} matching chunk(s) across {docs} document(s)'
    },
    grepResults: {
      chunkHits: '{count} chunks',
      keywordHits: '{count} hits',
      titleMatch: 'title',
      faqEntry: 'FAQ entry'
    },
    knowledgeChunksList: {
      chunkRange: 'Loaded {fetched} / {total} chunks',
      page: 'Page {page}, {pageSize} per page',
      offsetRange: 'Chunks {from}–{to}',
      queryMatches: '{count} matches for "{query}" in this document',
      queryNoMatch: 'No matches for "{query}" in this document'
    },
    attachmentParsing: {
      parsedSummary: 'Parsed {count} attachment(s)',
      parsedWithSkipped: 'Parsed {parsed} attachment(s), {skipped} skipped (still processing)',
      noneReady: 'No parsed attachments available'
    },
    ragPipeline: {
      searching: 'Searching knowledge base...',
      searchingWithQuery: 'Searching knowledge base: "{query}"',
      searchingWeb: 'Searching the web...',
      searchingWebWithQuery: 'Searching the web: "{query}"',
      searchingMixed: 'Searching knowledge base and web...',
      searchingMixedWithQuery: 'Searching knowledge base and web: "{query}"',
      searchDone: 'Search complete'
    },
    mcp: {
      discoverTools: 'Discover MCP tools',
      listServers: 'List MCP services',
      listTools: 'List MCP tools',
      searchTools: 'Search MCP tools',
      describeTool: 'Read tool definition',
      callTool: 'Call MCP tool',
      showing: 'Showing {count} of {total}',
      moreAvailable: 'More results available',
      empty: 'Nothing to show',
      parameters: 'Parameters',
      expand: 'Show more',
      collapse: 'Show less',
      required: 'Required',
      fullSchema: 'Full parameter definition',
      failed: 'MCP operation failed',
      result: 'Result'
    },
    toolStatus: {
      calling: 'Calling {name}...',
      searchKb: 'Searching knowledge base',
      searchKbFailed: 'Knowledge base search failed',
      searchMixed: 'Searched knowledge base and web',
      searchMixedFailed: 'Search failed',
      webSearch: 'Web search',
      webSearchFailed: 'Web search failed',
      grepSearch: 'Keyword search',
      grepSearchFailed: 'Keyword search failed',
      getDocInfo: 'Getting document info',
      getDocInfoFailed: 'Failed to get document info',
      viewDocument: 'View document',
      thinkingDone: 'Thinking complete',
      thinkingFailed: 'Thinking failed',
      updateTodos: 'Updating task list',
      updateTodosFailed: 'Failed to update task list',
      imageAnalyzing: 'Viewing image content...',
      imageAnalysisDone: 'Image content viewed',
      imageAnalysisFailed: 'Image viewing failed',
      attachmentParsing: 'Parsing attachments...',
      attachmentParsingDone: 'Attachments parsed',
      attachmentParsingFailed: 'Attachment parsing failed',
      queryUnderstanding: 'Understanding query...',
      queryUnderstandDone: 'Query understood',
      called: 'Called {name}',
      calledFailed: 'Failed to call {name}',
      shellExecRunning: 'Running sandbox command...'
    },
    copy: {
      emptyContent: 'Current response is empty, cannot copy',
      success: 'Copied to clipboard',
      failed: 'Copy failed, please copy manually'
    },
    saveToKb: {
      emptyContent: 'Current response is empty, cannot save to knowledge base',
      editorOpened: 'Editor opened, please select a knowledge base and save'
    }
  },
  agentEditor: {
    builtinHint: 'This is a built-in agent. Name and description cannot be modified, but configuration parameters can be adjusted.',
    navGroups: {
      basic: 'Basics',
      knowledge: 'Knowledge & Retrieval',
      capability: 'Extensions'
    },
    questionSuggestions: {
      title: 'Conversation question suggestions'
    },
    placeholders: {
      available: 'Available variables: ',
      clickToInsert: '(click to insert)',
      hint: '(click to insert, or type {\'{{\'} to show list)'
    },
    intentPrompts: {
      title: 'Intent Prompts',
      sectionDesc: 'Configure intent-specific system prompts; defaults apply when not customized',
      intentLabel: 'Intent',
      promptPlaceholder: 'Enter a custom system prompt...',
      customized: 'Customized',
      empty: 'No intent templates available'
    },
    promptNav: {
      ariaLabel: 'Prompt outline',
      system: 'System prompt',
      context: 'Context template',
      intent: 'Intent prompts',
      rewriteSystem: 'Rewrite · System',
      rewriteUser: 'Rewrite · User',
      fallback: 'Retrieval fallback'
    },
    selection: {
      all: 'All',
      selected: 'Selected',
      disabled: 'Disabled'
    },
    desc: {
      name: 'Set an easily identifiable name for the agent',
      description: 'Briefly describe the purpose and features of the agent',
      systemPrompt: 'Custom system prompt to define the agent behavior and role',
      promptInheritance: 'Unchanged template text follows template updates; edited text is saved as a custom prompt. In agent mode, this field defines the role and workflow; tool permissions and per-turn source selections are controlled separately.',
      useCustomSystemPrompt: 'Replace default persona',
      useCustomSystemPromptDesc: 'When enabled, this prompt replaces the platform default persona section; tool usage and citation contracts are still injected by the platform. When disabled, it is appended as extra instructions after the default persona.',
      leaveEmptyDefault: '(leave empty to use system default)',
      contextTemplate: 'Define how retrieved content is formatted before passing to the model',
      model: 'Select the LLM used by the agent',
      temperature: 'Control output randomness, 0 is most deterministic, 1 is most random',
      maxTokens: 'Maximum tokens for the model reply. Default is 2048. Custom values are saved as entered.',
      maxTokensAgent: 'Maximum tokens generated in each reasoning round, including tool-call JSON. Defaults to 24576. A custom value is saved as entered.',
      thinking: 'Enable extended thinking capability (requires model support)',
      queryUnderstandModel: 'Model used for query understanding (rewriting and intent detection). Leave empty to reuse the main chat model.',
      rewriteSystemPrompt: 'System prompt for question rewriting (leave empty for default)',
      rewriteUserPrompt: 'User prompt template for question rewriting (leave empty for default)',
      selectTools: 'Select tools available to the Agent',
      maxIterations: 'Limits model calls made by the main agent in one turn.',
      kbScope: 'Select the scope of knowledge bases accessible to the agent',
      fallbackStrategy: 'How to handle when no relevant content is found in the knowledge base',
      fallbackResponse: 'Fixed text returned when unable to answer',
      fallbackPrompt: 'Prompt to guide model response when no answer is found in knowledge base',
      memoryEnabled: 'Let this agent read and add to your long-term memory. When off, conversations with it neither read your memories nor add new ones. Turning it on here has no effect while the workspace or personal switch is off'
    },
    tools: {
      thinking: 'Thinking',
      thinkingDesc: 'Dynamic and reflective problem-solving thinking tool',
      todoWrite: 'Plan',
      todoWriteDesc: 'Create structured research plans',
      askUser: 'Ask User',
      askUserDesc: 'Ask the user for missing information and wait for the answer before continuing',
      searchKnowledge: 'Search knowledge',
      searchKnowledgeDesc: 'Semantic, keyword or hybrid search over knowledge-base chunks',
      readDocument: 'Read document',
      readDocumentDesc: 'Read a document\'s metadata and chunks, with paging and in-document search',
      listDocuments: 'List documents',
      listDocumentsDesc: 'Page through the documents of a knowledge base',
      queryGraph: 'Query Knowledge Graph',
      queryGraphDesc: 'Query relationships from knowledge graph',
      dbQuery: 'Query Database',
      dbQueryDesc: 'Query information from the database',
      dataAnalysis: 'Data Analysis',
      dataAnalysisDesc: 'Understand data files and perform data analysis',
      dataSchema: 'View Data Schema',
      dataSchemaDesc: 'Get metadata of tabular files',
      requiresKb: '(requires knowledge base configuration)',
      requiresRagKb: '(requires a KB with vector/keyword indexing enabled)',
      requiresWikiKb: '(requires a Wiki-enabled knowledge base)',
      wikiSearch: 'Search Wiki',
      wikiSearchDesc: 'Keyword / semantic search over Wiki pages',
      wikiReadPage: 'Read Wiki Page',
      wikiReadPageDesc: 'Read the full content of a specific Wiki page',
      wikiFlagIssue: 'Flag Wiki Issue',
      wikiFlagIssueDesc: 'Flag factual errors or merge conflicts on a Wiki page',
      wikiWritePage: 'Create / Overwrite Wiki',
      wikiWritePageDesc: 'Create a new page or fully overwrite an existing one',
      wikiReplaceText: 'Replace Text in Wiki',
      wikiReplaceTextDesc: 'Replace specific text in a Wiki page',
      wikiRenamePage: 'Rename Wiki Page',
      wikiRenamePageDesc: 'Rename a Wiki page and auto-update cross-links',
      wikiDeletePage: 'Delete Wiki Page',
      wikiDeletePageDesc: 'Delete a Wiki page and clean up dead links',
      wikiReadIssue: 'View Wiki Issue',
      wikiReadIssueDesc: 'View details of a Wiki page issue',
      wikiUpdateIssue: 'Update Wiki Issue',
      wikiUpdateIssueDesc: 'Update the status of a Wiki page issue',
      webSearch: 'Web Search',
      webFetch: 'Web Fetch',
      groupBase: 'Basic',
      groupRag: 'Knowledge Retrieval (RAG)',
      groupWikiRead: 'Wiki Read',
      groupWikiEdit: 'Wiki Edit',
      groupWikiIssue: 'Wiki Review',
      groupData: 'Data Analysis',
      writeWarning: 'Mutates Wiki content',
      dangerTag: 'Write',
      statusNoKb: 'No knowledge base is linked',
      kbMetricRag: 'RAG KBs',
      kbMetricWiki: 'Wiki KBs',
      statusInactive: '{count} ticked tool(s) cannot take effect with the current config',
      searchConversations: 'Search past conversations',
      searchConversationsDesc: 'Look up what was discussed in this user\'s own earlier conversations',
      groupStored: 'Stored, not offered here',
      switchManagedDesc: 'Controlled by other settings of this agent, not by this list, so ticking it here does not turn it on. Untick it to remove it.',
      unrecognizedDesc: 'Not a tool this version offers, so the agent cannot call it. Untick it to remove it.',
      keptUnknownWarning: 'Saved. These stored tools are not offered by this version and were kept, but the agent cannot call them: {names}',
      droppedWarning: 'Saved. These tools are controlled by other settings of this agent and were removed from the tool list: {names}',
      effectiveLabel: 'Effective Tools',
      effectiveDesc: 'Computed from the current config — these are the tools the agent will actually be able to call',
      effectiveEmpty: 'No tool available — the agent will fall back to plain model chat'
    },
    embed: {
      title: 'Web Page Embed'
    },
    im: {
      title: 'IM Integration',
      description: 'Connect agent to instant messaging platforms like WeCom, Feishu, Lark, Slack, Telegram, DingTalk, Mattermost, WeChat, QQBot and Yunzhijia',
      feishu: 'Feishu',
      lark: 'Lark',
      slack: 'Slack',
      telegram: 'Telegram',
      dingtalk: 'DingTalk',
      mattermost: 'Mattermost',
      wecom: 'WeCom',
      wechat: 'WeChat',
      qqbot: 'QQBot',
      yunzhijia: 'Yunzhijia',
      addChannel: 'Add Channel',
      channelsTitle: 'IM Channels',
      disabled: 'Disabled',
      editChannel: 'Edit Channel',
      deleteConfirm: 'Are you sure you want to delete this channel? This action cannot be undone.',
      channelName: 'Channel Name',
      channelNamePlaceholder: 'Enter a name for easy identification',
      channelNameDefaultHint: 'Defaults to the platform name; you can customize it, or leave blank to use the platform name on save',
      platform: 'Platform',
      mode: 'Connection Mode',
      outputMode: 'Output Mode',
      outputStream: 'Streaming',
      outputFull: 'Full Response',
      callbackUrl: 'Callback URL',
      empty: 'No IM channels yet',
      unnamed: 'Unnamed Channel',
      docLink: 'Integration Guide',
      wecomConsole: 'WeCom Admin Console',
      feishuConsole: 'Feishu Open Platform',
      larkConsole: 'Lark Open Platform',
      slackConsole: 'Slack API Console',
      telegramConsole: 'Telegram BotFather',
      dingtalkConsole: 'DingTalk Open Platform',
      dingtalkCardTemplateId: 'Card Template ID (optional)',
      dingtalkCardTemplateIdHint: 'Create an AI Card template at open-dev.dingtalk.com/fe/card to enable streaming output with typewriter effect',
      mattermostConsole: 'Mattermost integrations',
      qqbotConsole: 'QQ Open Platform',
      qqbotAPIBaseURLHint: 'Optional. Leave empty to use the default production API endpoint.',
      qqbotGatewayURLHint: 'Optional. Leave empty to fetch the common WebSocket gateway automatically.',
      yunzhijiaConsole: 'Yunzhijia Open Platform',
      yunzhijiaRobotDoc: 'Robot messaging docs',
      yunzhijiaImageDoc: 'Developer platform (images)',
      yunzhijiaModeHint: 'Supports Webhook and WebSocket; WebSocket mode does not require a public callback URL.',
      yunzhijiaSendMsgUrl: 'Send Message URL',
      yunzhijiaSendMsgUrlHint: 'Used for robot replies.',
      yunzhijiaSecret: 'Signature Secret (optional)',
      yunzhijiaSecretPlaceholder: 'HmacSHA1 signature secret from Yunzhijia robot settings',
      yunzhijiaSecretHint: 'If configured, incoming callbacks will be verified using HmacSHA1 signature',
      yunzhijiaAppId: 'App ID (image download)',
      yunzhijiaAppIdPlaceholder: 'Yunzhijia Open Platform App ID',
      yunzhijiaAppSecret: 'App Secret (image download)',
      yunzhijiaAppSecretPlaceholder: 'Yunzhijia Open Platform App Secret',
      yunzhijiaAppCredentialHint: 'Used to obtain appAccessToken and download images sent by users.',
      yunzhijiaTimeout: 'HTTP Timeout (seconds)',
      yunzhijiaTimeoutHint: 'Timeout for sending replies via Send Message URL, default 10 seconds',
      yunzhijiaAllowedHostSuffix: 'Allowed Host Suffix',
      yunzhijiaAllowedHostSuffixHint: 'Restrict Send Message URL host to this suffix for security (e.g. yunzhijia.com)',
      yunzhijiaSendMsgUrlRequired: 'Enter the Send Message URL from Yunzhijia robot settings',
      mattermostModeHint: 'Mattermost only supports Webhook mode (outgoing webhook + bot token).',
      mattermostPostToMain: 'Post replies in channel timeline',
      mattermostPostToMainHint: 'When on, bot replies are new top-level posts in the channel. When off (default), they stay in the thread and the main view only shows “N replies”.',
      modeHint: 'WebSocket is recommended for easier setup',
      consoleTip: 'to get credentials',
      wecomWSEndpointHint: 'Optional. For private WeCom deployments, enter a custom WebSocket address. Leave empty to use the default public cloud endpoint. For internal network addresses, add the hostname to the SSRF_WHITELIST env var.',
      wecomAPIBaseURLHint: 'Optional. For private WeCom deployments, enter a custom API base URL. Leave empty to use the default public cloud endpoint. For internal network addresses, add the hostname to the SSRF_WHITELIST env var.',
      feishuAPIBaseURLHint: 'Optional. Leave empty if the server can reach the internet directly; if a proxy is required to access Feishu, enter the reverse proxy URL (e.g. nginx, http://host:port). For internal network addresses, add the hostname to the SSRF_WHITELIST env var.',
      fileKnowledgeBase: 'File Storage Knowledge Base',
      fileKnowledgeBasePlaceholder: 'Select a knowledge base (optional)',
      fileKnowledgeBaseHint: 'When configured, files sent by users will be automatically saved to this knowledge base',
      sessionMode: 'Session Mode',
      sessionModeUser: 'Per User (default)',
      sessionModeThread: 'Per Thread',
      sessionModeHint: 'User mode: each person has their own conversation. Use /clear to start fresh. Thread mode: each message thread is a separate conversation. Multiple people can collaborate in the same thread.',
      replyLanguage: 'Reply Language',
      replyLanguageDefault: 'Use system default',
      replyLanguageHint: 'Fix the agent reply language for this channel. Leave unset to use the deployment default.',
      wechatScanBind: 'Scan to bind WeChat',
      wechatScanning: 'Scan the QR code with WeChat',
      wechatBindSuccess: 'WeChat bound successfully',
      wechatRebind: 'Rebind',
      wechatHint: 'Requires iOS WeChat 8.0.70+, direct messages only',
      wechatQRExpired: 'QR code expired, please try again',
      wechatBinding: 'Binding...',
      sectionChannel: 'Channel info',
      sectionConnection: 'Connection',
      sectionCredentials: 'Platform credentials',
      selectPlatform: 'Select platform',
      selectPlatformDesc: 'Choose the messaging platform to connect',
      enabled: 'Enable channel',
      stepBasic: 'Basic info',
      stepConnection: 'Connection',
      stepKnowledge: 'File storage',
      stepCredentials: 'Credentials',
      sectionAccess: 'Access & output',
      sectionSession: 'Session',
      sectionCallback: 'Callback URL',
      sectionKnowledge: 'File storage',
      sectionStatus: 'Status'
    },
    agentType: {
      label: 'Agent Type',
      desc: 'Picking a preset auto-fills the system prompt, tool list and recommended KB scope.',
      defaultNamePattern: 'My {label}',
      kbMismatch: {
        ragQa: 'RAG retrieval not enabled',
        wikiQa: 'Wiki not enabled',
        hybridRagWiki: 'No retrieval surface enabled',
        dataAnalysis: 'Requires RAG (FAQ not supported)',
        quickAnswer: 'Quick Answer mode requires RAG retrieval',
        generic: 'Not compatible with current type'
      },
      kbIncompatibleWarn: '{count} selected KB(s) are not compatible with this type, please adjust manually.'
    },
    mcp: {
      label: 'MCP Services',
      desc: 'Select MCP services available to the Agent',
      selectLabel: 'Select MCP Services',
      selectDesc: 'Select MCP services to enable',
      selectPlaceholder: 'Select MCP services',
      authWaitTimeout: 'Authentication Wait Timeout (s)',
      authWaitTimeoutDesc: 'Maximum seconds to wait for you to complete OAuth authentication when prompted during a conversation; the prompt is skipped after it elapses (only affects OAuth MCP services).',
      authWaitTimeoutPlaceholder: 'Default 600 seconds',
      accessLevel: 'Access level',
      accessLevelDesc: 'Whether tools that change data (MCP tools, Wiki writes) run without asking. Read-only leaves them out; confirm asks you each time. MCP tools marked as requiring approval always ask.',
      unavailableService: 'Unavailable service'
    },
    llmCallTimeout: {
      label: 'LLM Call Timeout',
      desc: 'Request timeout for the model client (seconds). A streaming response that keeps producing output may run longer than this value.',
      hint: 'Leave empty or 0 to use the default (120 seconds)',
      placeholder: 'Enter seconds, recommended range 60-1800'
    },
    imageUpload: {
      navLabel: 'Attachment Upload',
      sectionTitle: 'Attachment Upload',
      sectionDesc: 'Configure image, document, and audio attachments in chat, plus parse rules and related models',
      label: 'Image Upload',
      desc: 'Allow users to upload images in chat for VLM understanding',
      vlmModel: 'VLM Model',
      vlmModelDesc: 'Vision language model for image analysis',
      vlmModelPlaceholder: 'Select VLM model',
      vlmModelRequired: 'VLM model is required when image upload is enabled',
      imageUnderstandingLabel: 'Attachment Image Understanding / Scanned OCR',
      imageUnderstandingDesc: 'For image-only PDFs/PPTs (scanned documents), run VLM OCR when no text can be extracted. Increases parse latency; off by default.',
      ocrMaxPagesLabel: 'Scanned OCR Max Pages',
      ocrMaxPagesDesc: 'Max pages of a scanned document sent to the VLM for OCR. More pages means better coverage but slower and costlier parsing. 0 uses the global default.',
      useGlobalDefault: '0 = global default',
      storageProvider: 'Image Storage',
      storageProviderDesc: 'Storage engine for uploaded images. Leave empty to use system default',
      storageProviderPlaceholder: 'Select storage engine',
      storageDefault: 'System Default',
      notConfigured: 'Not Configured',
      goStorageSettings: 'Go to Storage Settings'
    },
    audioUpload: {
      label: 'Audio Upload',
      desc: 'When enabled, users can upload audio files in conversations. The system will automatically transcribe them using the ASR model.',
      asrModel: 'ASR Model',
      asrModelDesc: 'Speech recognition model for audio transcription. If not configured, audio files will be passed as placeholders.',
      asrModelPlaceholder: 'Select ASR Model'
    },
    chatParser: {
      label: 'Chat Attachment Parsing Policy',
      desc: 'Choose a parser engine per file type for this agent\'s chat attachments.',
      waitTimeoutLabel: 'Attachment Parse Wait Timeout (s)',
      waitTimeoutDesc: 'How long a chat turn waits for still-parsing attachments before proceeding with only the finished ones. Raise for large / scanned files. 0 uses the global default.'
    },
    faq: {
      title: 'FAQ Priority Strategy'
    },
    fallback: {
      fixed: 'Fixed Response',
      model: 'Model Generated'
    },
    fileTypes: {
      label: 'Supported File Types',
      desc: 'Restrict selectable file types, leave empty to support all types',
      allTypes: 'All Types',
      pdf: 'PDF Documents',
      word: 'Word Documents (.docx/.doc)',
      textLabel: 'Text',
      text: 'Plain Text Files (.txt)',
      markdown: 'Markdown Documents',
      csv: 'Comma-Separated Value Files',
      excel: 'Excel Spreadsheets (.xlsx/.xls)',
      imageLabel: 'Images',
      image: 'Image Files (.jpg/.jpeg/.png)'
    }
  },
  mermaid: {
    diagram: 'Diagram',
    expand: 'Expand',
    zoomIn: 'Zoom In',
    zoomOut: 'Zoom Out',
    reset: 'Reset',
    download: 'Download Image',
    close: 'Close',
    downloading: 'Downloading...'
  },
  datasource: {
    title: 'Data Sources',
    description: 'Configure external data sources to sync content into this knowledge base',
    add: 'Add Data Source',
    empty: 'No data sources configured',
    edit: 'Edit',
    delete: 'Delete',
    deleteConfirm: 'Delete this data source? Synced knowledge will not be removed.',
    deleteSuccess: 'Data source deleted',
    deleteFailed: 'Failed to delete',
    syncNow: 'Sync Now',
    syncTriggered: 'Sync task submitted',
    syncFailed: 'Failed to trigger sync',
    pause: 'Pause',
    resume: 'Resume',
    paused: 'Paused',
    resumed: 'Resumed',
    pauseFailed: 'Failed to pause',
    logs: 'Logs',
    syncModeLabel: 'Sync mode',
    parseModeLabel: 'Parse mode',
    parseMode: {
      inherit: 'Use server setting',
      blocks: 'Blocks (default)',
      export: 'Export (docx)'
    },
    parseModeHint: 'How Feishu cloud documents are parsed. Blocks is faster and keeps in-document attachments; Export converts documents to docx for parsing and keeps images associated with the document.',
    syncMode: {
      incremental: 'Incremental',
      full: 'Full'
    },
    status: {
      active: 'Connected',
      paused: 'Paused',
      error: 'Error'
    },
    createTitle: 'Add Data Source',
    editTitle: 'Edit Data Source',
    nameLabel: 'Name',
    namePlaceholder: 'Enter data source name',
    sectionBasic: 'Basic information',
    testConnection: 'Test Connection',
    testSuccess: 'Connection successful',
    testFailed: 'Connection failed',
    connected: 'Connected',
    connectionFailed: 'Connection failed',
    isRequired: 'is required',
    credentialsLabel: 'credentials',
    gitlab: {
      baseUrl: 'GitLab URL',
      accessToken: 'Personal access token',
      projects: 'GitLab projects',
      projectsHint: 'Enter a project ID or namespace path (for example group/project), with optional branch and directories.',
      project: 'Project',
      projectId: 'Project ID',
      projectIdPlaceholder: 'For example: 12345 or group/project',
      ref: 'Branch',
      refPlaceholder: 'Leave empty to use the default branch',
      paths: 'Directories',
      pathsPlaceholder: 'One directory per line; leave empty to sync the whole project',
      addProject: 'Add project',
      projectRequired: 'Add at least one GitLab project'
    },
    nextcloud: {
      baseUrl: 'Nextcloud URL',
      baseUrlHint: 'Installation URL, for example https://nextcloud.example.com/cloud, without /remote.php/dav. Private deployments must use the existing SSRF_WHITELIST.',
      username: 'Username',
      appPassword: 'App password',
      appPasswordHint: 'Create an app password under Personal settings → Security → Devices & sessions. Use the generated username and app password.',
      selectionRequired: 'Select at least one folder or file',
      includeExtensions: 'Include extensions (optional)',
      excludeExtensions: 'Exclude extensions (optional)',
      extensionsHint: 'Comma-separated extensions, for example .pdf, .md. Empty includes all supported formats; exclusions take priority. Changing filters also changes the deletion scope.'
    },
    seafile: {
      baseUrl: 'Seafile URL',
      apiToken: 'API token',
      apiTokenHint: 'Generate it under "Settings → Web API token" in Seafile; the account only needs read access to the libraries you select, and the token is never sent with file downloads.',
      singleLibraryOnly: 'A data source syncs one library; clear the current library before selecting another.',
      selectionRequired: 'Select at least one library, folder or file'
    },
    resourceHint: 'Select the spaces or folders to sync',
    untitled: 'Untitled',
    resourceLoadFailed: 'Failed to load resources',
    noResources: 'No wiki spaces found',
    noResourcesDesc: 'The app needs wiki access via a group chat to fetch content',
    noResourcesDesc_notion: 'The app needs Notion page access permissions to fetch content',
    retryLoadResources: 'Retry',
    guideStep1: 'Create a group chat in Feishu, then add your app as a bot in the group settings',
    guideStep2: 'Open wiki "Settings" > "Member Settings" > "Add Member", search for the group chat and add it',
    guideStep3: 'Ensure the group chat role is at least "Can Read", then come back and click Retry',
    guideStep1_notion: 'Open the page or database you want to sync in Notion',
    guideStep2_notion: 'Click the "···" menu at the top right, select "Connect to" or "Add connections"',
    guideStep3_notion: 'Search and select your Integration app, then come back and click Retry',
    noResourcesDesc_nextcloud: 'No accessible folders or supported files were found',
    guideStep1_nextcloud: 'Sign in to Nextcloud and verify read access to the selected folders',
    guideStep2_nextcloud: 'Create an app password under Personal settings → Security → Devices & sessions',
    guideStep3_nextcloud: 'Replace the credentials here, then retry loading resources',
    noResourcesDesc_seafile: 'The token can reach no libraries, or every library is encrypted (encrypted libraries cannot be synced)',
    guideStep1_seafile: 'Sign in to Seafile and confirm the account can read at least one unencrypted library',
    guideStep2_seafile: 'Generate or regenerate the token under "Settings → Web API token"',
    guideStep3_seafile: 'Come back, enter the new token and click Retry',
    permissionDocLink: 'View Feishu wiki permission docs',
    syncScheduleLabel: 'Sync schedule',
    conflictLabel: 'Conflict strategy',
    conflict: {
      overwrite: 'Overwrite',
      skip: 'Skip existing'
    },
    syncDeletions: 'Sync deletions (remove knowledge when deleted at source)',
    createAndSync: 'Create & Sync Now',
    createAndSyncSuccess: 'Data source created and sync task submitted',
    createButSyncFailed: 'Data source created, but failed to trigger sync',
    updateSuccessSyncHint: 'Data source updated. Editing does not start a sync automatically; click Sync to import changes.',
    saveFailed: 'Failed to save',
    step: {
      selectType: 'Select Type',
      credentials: 'Credentials',
      resources: 'Resources',
      strategy: 'Strategy'
    },
    syncHistory: 'Sync History',
    refreshLogs: 'Refresh logs',
    noLogs: 'No sync records yet',
    logStatus: {
      running: 'Syncing',
      success: 'Success',
      partial: 'Partial',
      failed: 'Failed',
      canceled: 'Canceled'
    },
    logMetric: {
      total: 'Total',
      skipped: 'skipped',
      failed: 'failed'
    },
    logSummary: {
      total: 'Runs',
      success: 'Success',
      failed: 'Failed',
      items: 'Items'
    },
    logDetail: {
      startTime: 'Started',
      endTime: 'Finished',
      failedItems: 'Failed documents',
      failedItemsMore: '{n} more failed documents not shown',
      docsFailedSummary: '{n} document(s) failed to sync'
    },
    connector: {
      feishu: 'Feishu',
      lark: 'Lark',
      feishu_drive: 'Feishu Drive',
      lark_drive: 'Lark Drive',
      notion: 'Notion',
      confluence: 'Confluence',
      yuque: 'Yuque',
      dingtalk: 'DingTalk Docs',
      rss: 'RSS / Atom Feed',
      ima: 'Tencent IMA',
      gitlab: 'GitLab',
      nextcloud: 'Nextcloud',
      seafile: 'Seafile'
    },
    connectorDesc: {
      feishu: 'Sync documents, spreadsheets and files from Feishu Wiki',
      lark: 'Sync documents, spreadsheets and files from Lark Wiki (Feishu international)',
      feishu_drive: 'Sync documents, spreadsheets and files from a Feishu Drive folder',
      lark_drive: 'Sync documents, spreadsheets and files from a Lark Drive folder (Feishu international)',
      notion: 'Sync pages and databases from Notion',
      confluence: 'Sync spaces and pages from Confluence as Markdown',
      yuque: 'Sync documents from Yuque knowledge bases',
      dingtalk: 'Sync online documents from DingTalk knowledge bases',
      rss: 'Sync articles from RSS / Atom feeds',
      ima: 'Sync documents, notes and files from Tencent IMA knowledge bases (AI sessions and video parses are not supported)',
      gitlab: 'Sync files from GitLab projects',
      nextcloud: 'Sync folders and files from Nextcloud over WebDAV',
      seafile: 'Sync folders and files from Seafile libraries'
    },
    drive: {
      folderTokenLabel: 'Drive folder token',
      folderTokenPlaceholder: 'Enter a folder_token or a Feishu Drive folder URL',
      folderTokenRequired: 'Please enter a concrete folder_token; the cloud-space root is not supported',
      rootNotSupportedHint: 'The root folder is not paginated and does not return shortcuts; pick a concrete folder',
      load: 'Load',
      shareHint: 'Share the Drive folder with the app’s group first, otherwise the app cannot access it',
      placeholderTitle: 'Load a Drive folder first',
      placeholderDesc: 'Enter a folder_token (or paste a Feishu Drive folder URL) above and click "Load"',
      loadForbiddenHint: 'The app has no access to this folder. Share the folder with the app’s group in Feishu Drive and retry.',
      loadAuthHint: 'App credentials are invalid or missing Drive scopes. Check App ID / App Secret and drive:drive:readonly permissions.',
      loadNotFoundHint: 'folder_token does not exist or has been deleted. Verify the token copied from the Feishu Drive folder URL.'
    },
    field: {
      appId: 'App ID',
      appSecret: 'App Secret',
      clientId: 'Client ID',
      clientSecret: 'Client Secret',
      operatorId: 'Operator Union ID',
      operatorIdHint: 'Reads knowledge bases with this user’s permissions. Obtain it from the DingTalk user details API.',
      integrationToken: 'Integration Token',
      apiToken: 'API Token',
      confluenceEdition: 'Edition',
      confluenceEditionServer: 'Server / Data Center',
      confluenceEditionCloud: 'Cloud',
      confluenceBaseUrl: 'Confluence URL',
      confluenceUsername: 'Username or email',
      confluencePat: 'Server/DC personal access token (PAT)',
      confluencePatHint: 'Optional. When provided, uses Bearer authentication; username and password are not required.',
      confluencePassword: 'Server/DC password',
      confluenceApiToken: 'Cloud API token',
      imaClientId: 'IMA ClientID',
      imaApiKey: 'IMA APIKey',
      baseUrl: 'Base URL (optional)',
      baseUrlHint: 'Leave empty to use the default public cloud address. For private/enterprise deployments or when accessing via reverse proxy, enter your custom address (e.g. https://api-proxy.example.com).',
      feedUrls: 'Feed URLs',
      feedUrlsHint: 'One RSS / Atom feed URL per line; multiple feeds are supported.',
      authHeaders: 'Custom headers (optional)',
      authHeadersHint: 'For private feeds. One per line in "Name: Value" form, e.g. Authorization: Bearer xxxx'
    },
    confluence: {
      cloudFolderLimitation: 'Confluence Cloud cannot list pages stored directly under top-level folders in this space; selecting the whole space still syncs them.'
    },
    comingSoon: 'Coming soon',
    docHint: 'Get credentials at:',
    openDoc: 'Open documentation',
    prereqBarText: 'First time? Click to see Feishu app setup guide',
    prereqBarText_yuque: 'First time? Click to see the Yuque token setup guide',
    prereqStep1Brief_yuque: 'Create a Yuque personal token',
    prereqStep1Desc_yuque: 'Sign in to Yuque → avatar → Settings → Token → New Token',
    prereqStep2Brief_yuque: 'Grant the token required permissions',
    prereqStep2Desc_yuque: 'Check at least repo:read and doc:read (read knowledge base and document content)',
    prereqStep3Brief_yuque: '(Optional) Enter Base URL for enterprise deployments',
    prereqStep3Desc_yuque: 'Leave empty for public cloud; for Yuque Enterprise or self-hosted, enter your company domain.',
    prereqStep1Brief_feishu: 'Create Feishu custom app',
    prereqStep1Desc_feishu: 'Login Feishu Open Platform → Create enterprise custom app',
    prereqStep2Brief_feishu: 'Add bot capability',
    prereqStep2Desc_feishu: 'Open Platform → Your app → Add app capability → Bot',
    prereqStep3Brief_feishu: 'Configure app permissions',
    prereqStep3Desc_feishu: 'Enable wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly permissions',
    prereqStep1Brief_lark: 'Create Lark custom app',
    prereqStep1Desc_lark: 'Login Lark Open Platform → Create enterprise custom app',
    prereqStep2Brief_lark: 'Add bot capability',
    prereqStep2Desc_lark: 'Open Platform → Your app → Add app capability → Bot',
    prereqStep3Brief_lark: 'Configure app permissions',
    prereqStep3Desc_lark: 'Enable wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly permissions',
    prereqStep1Brief_feishu_drive: 'Create Feishu custom app',
    prereqStep1Desc_feishu_drive: 'Login Feishu Open Platform → Create enterprise custom app',
    prereqStep2Brief_feishu_drive: 'Add bot capability',
    prereqStep2Desc_feishu_drive: 'Open Platform → Your app → Add app capability → Bot',
    prereqStep3Brief_feishu_drive: 'Configure app permissions',
    prereqStep3Desc_feishu_drive: 'Enable drive:drive:readonly, drive:export:readonly, docx:document:readonly permissions',
    prereqStep1Brief_lark_drive: 'Create Lark custom app',
    prereqStep1Desc_lark_drive: 'Login Lark Open Platform → Create enterprise custom app',
    prereqStep2Brief_lark_drive: 'Add bot capability',
    prereqStep2Desc_lark_drive: 'Open Platform → Your app → Add app capability → Bot',
    prereqStep3Brief_lark_drive: 'Configure app permissions',
    prereqStep3Desc_lark_drive: 'Enable drive:drive:readonly, drive:export:readonly, docx:document:readonly permissions',
    prereqOpenConsole_yuque: 'Open Yuque Token settings',
    yuqueFolderModeLabel: 'Folder structure',
    yuqueFolderModeToc: 'Mirror the Yuque TOC',
    yuqueFolderModeNone: 'Keep everything flat',
    yuqueFolderModeHint: 'Files documents by their Yuque table-of-contents path. Note: folder moves made in the knowledge base afterwards are overwritten by the Yuque structure the next time that document syncs.',
    yuqueTOCOnly: 'Sync only documents visible in the Yuque TOC',
    yuqueTOCOnlyHint: 'Requires the "Mirror the Yuque TOC" layout. Documents already in the knowledge base are untouched — one the Yuque TOC does not list is simply no longer added, never deleted.',
    dingtalkIngestLabel: 'DingTalk ingestion scope',
    dingtalkIncludeUploadedFiles: 'Ingest uploaded files (docx / pptx / xlsx / pdf)',
    dingtalkIncludeUploadedFilesHint: 'Off by default. When on, Word / PowerPoint / Excel / PDF files uploaded to the selected scope are downloaded and parsed into the knowledge base, up to 64 MiB per file; their text counts towards storage and embedding cost. When off they are simply skipped — the sync log says the switch is not enabled, and copies already in the knowledge base are kept.',
    prereqBarText_dingtalk: 'First time? Click to see the DingTalk app setup guide',
    prereqStep1Brief_dingtalk: 'Create an internal enterprise app',
    prereqStep1Desc_dingtalk: 'Create an internal app in DingTalk Open Platform and copy its Client ID and Client Secret.',
    prereqStep2Brief_dingtalk: 'Grant knowledge base read permissions',
    prereqStep2Desc_dingtalk: 'Grant Wiki.Workspace.Read, Wiki.Node.Read, and Storage.File.Read.',
    prereqStep3Brief_dingtalk: 'Enter the operator Union ID',
    prereqStep3Desc_dingtalk: 'Enter the Union ID of a DingTalk user who can access the target knowledge bases.',
    prereqOpenConsole_dingtalk: 'Open DingTalk Developer Console',
    prereqBarText_ima: 'First time? Click to see the Tencent IMA OpenAPI setup guide',
    prereqStep1Brief_ima: 'Enable IMA agent OpenAPI access',
    prereqStep1Desc_ima: 'Sign in to https://ima.qq.com/agent-interface and apply for OpenAPI access',
    prereqStep2Brief_ima: 'Obtain the ClientID and APIKey',
    prereqStep2Desc_ima: 'Copy the ima-openapi-clientid and ima-openapi-apikey credentials from the agent-interface page',
    prereqStep3Brief_ima: 'Grant the credential access to the target knowledge bases',
    prereqStep3Desc_ima: 'In the IMA client, authorize the credential for the knowledge bases you want to sync; unauthorized bases will not appear in the list',
    prereqOpenConsole_ima: 'Open Tencent IMA OpenAPI console',
    prereqBotBrief: 'Add "Bot" capability to your app',
    prereqBotDesc: 'Open Platform > Add App Capability > Bot > create version and publish',
    prereqPermBrief: 'Grant API permissions',
    prereqOpenConsole: 'Open Feishu Developer Console',
    prereqMemberBrief: 'Add app to wiki via group chat',
    prereqMemberDesc: 'Create group chat > add app as bot > add group chat as wiki member',
    back: 'Back',
    next: 'Next',
    save: 'Save',
    schedule30min: 'Every 30 min',
    schedule1h: 'Every hour',
    schedule6h: 'Every 6 hours',
    schedule12h: 'Every 12 hours',
    schedule24h: 'Daily',
    scheduleHuman: {
      '30min': 'Every 30 min',
      '1h': 'Hourly',
      '6h': 'Every 6 hours',
      '12h': 'Every 12 hours',
      '24h': 'Daily'
    },
    resourceType: {
      wikiSpace: 'Wiki Space',
      docCategory: 'Document Tag',
      book: 'Yuque Book',
      library: 'Seafile Library'
    },
    neverSynced: 'Never synced',
    justNow: 'Just now',
    minutesAgo: '{n}m ago',
    hoursAgo: '{n}h ago',
    daysAgo: '{n}d ago',
    syncError: {
      dingtalk_document_failed: 'DingTalk document could not be read; check access and retry the sync.',
      dingtalk_document_too_large: 'DingTalk file exceeds the 64 MiB download limit; skipped for this sync. Compress or split the file.',
      dingtalk_resource_failed: 'DingTalk resource is unavailable; check access and the saved selection, then retry.',
      deletion_lookup_failed: 'Failed to look up the item before deletion; see server logs',
      deletion_failed: 'Deletion failed; see server logs',
      ingest_failed: 'Ingest failed; see server logs',
      nextcloud_permission_denied: 'Access to the Nextcloud file was denied; check account permissions.',
      nextcloud_not_found: 'The Nextcloud file disappeared after listing; the next sync retries it.',
      nextcloud_file_too_large: 'The Nextcloud file exceeds MAX_FILE_SIZE_MB.',
      nextcloud_empty_file: 'The Nextcloud file is empty and was skipped.',
      nextcloud_source_changed: 'The Nextcloud file changed during download; the next sync retries it.',
      nextcloud_invalid_response: 'Nextcloud returned an invalid or incomplete WebDAV response.',
      nextcloud_ssrf_blocked: 'The Nextcloud request was blocked by the SSRF policy; check SSRF_WHITELIST.',
      nextcloud_fetch_failed: 'Failed to fetch the file from Nextcloud; the next sync retries it.',
      seafile_permission_denied: 'Access to the Seafile file was denied; check the library permissions of the token owner.',
      seafile_not_found: 'The Seafile file no longer exists or was moved; the next sync retries it.',
      seafile_file_too_large: 'The Seafile file exceeds the size limit; raise MAX_FILE_SIZE_MB or shrink the file.',
      seafile_empty_file: 'The Seafile file is empty and was skipped.',
      seafile_source_changed: 'The Seafile file changed while it was being fetched; the next sync retries it.',
      seafile_invalid_response: 'Seafile returned a response that could not be parsed; check the server version and reverse proxy.',
      seafile_ssrf_blocked: 'The Seafile download URL was blocked by the SSRF policy; add the fileserver host to SSRF_WHITELIST.',
      seafile_fetch_failed: 'Failed to fetch the file from Seafile; the next sync retries it.'
    }
  },
  integrations: {
    cli: {
      title: 'WeKnora CLI'
    },
    mcpserver: {
      title: 'MCP Server',
      groups: {
        retrieve: 'Retrieval & reading',
        chat: 'Question answering',
        wiki: 'Wiki',
        ingest: 'Writes (enable with care)'
      },
      tools: {
        list_knowledge_bases: 'List knowledge bases',
        list_knowledge_basesDesc: 'Return the knowledge bases in scope and the retrieval modes each supports',
        search_knowledge: 'Semantic search',
        search_knowledgeDesc: 'Find relevant passages for a natural-language question, with sources',
        grep_chunks: 'Keyword / regex search',
        grep_chunksDesc: 'Case-insensitive regex over raw chunks; best for exact terms, codes and names',
        list_documents: 'List documents',
        list_documentsDesc: 'Page through the documents of one knowledge base',
        read_document: 'Read document',
        read_documentDesc: 'Read a document\'s metadata and its chunks in order',
        ask: 'Ask',
        askDesc: 'Run the agent configured on this endpoint and return a cited answer; supports follow-up turns',
        wiki_search: 'Search wiki',
        wiki_searchDesc: 'Search the generated wiki pages',
        wiki_read_page: 'Read wiki page',
        wiki_read_pageDesc: 'Read one wiki page by slug',
        wiki_index: 'Browse wiki index',
        wiki_indexDesc: 'Show the table of contents of a knowledge base wiki',
        add_document: 'Add document',
        add_documentDesc: 'Add a document from Markdown text or a URL',
        update_document: 'Update document',
        update_documentDesc: 'Replace the content or title of a Markdown document',
        delete_document: 'Delete document',
        delete_documentDesc: 'Permanently delete a document and its index data'
      }
    },
    tabs: {
      im: 'IM Integration',
      embed: 'Web Embed',
      api: 'API Integration',
      chrome: 'Chrome Extension',
      cli: 'CLI',
      claw: 'Claw Skill',
      mcpserver: 'MCP Server'
    },
    api: {
      title: 'API Integration',
      updateApiKeyScopeFailed: 'Failed to update API key'
    },
    imOverview: {
      title: 'Connected IM channels'
    },
    embedOverview: {
      title: 'Web embed channels'
    },
    agentEditor: {
      desc: 'Publish this agent to IM platforms or websites. Manage in Integrations.'
    },
    chrome: {
      title: 'Knowledge Assistant'
    },
    claw: {
      title: 'WeKnora Skill'
    }
  },
  credential: {
    configured: 'Configured',
    unconfigured: 'Not configured',
    configure: 'Configure',
    update: 'Replace',
    remove: 'Remove',
    inputPlaceholder: 'Enter value',
    savedToast: 'Credential saved',
    saveFailed: 'Failed to save credential',
    removedToast: 'Credential removed',
    removeFailed: 'Failed to remove credential',
    confirmRemovePrompt: 'Remove this credential? This cannot be undone.',
    confirmRemove: 'Confirm remove'
  },
  userProfile: {
    title: 'User Profile',
    description: 'View your account info (user ID, username, account, registration time) and change your password.',
    changePassword: {
      label: 'Change password',
      description: 'Verify your current password, then set a new one. All signed-in sessions will be revoked and you will need to sign in again.',
      currentLabel: 'Current password',
      currentPlaceholder: 'Enter your current password',
      currentRequired: 'Enter your current password',
      newLabel: 'New password',
      newPlaceholder: 'Enter new password',
      confirmLabel: 'Confirm new password',
      confirmPlaceholder: 'Enter the new password again',
      submit: 'Update password',
      success: 'Password updated. Please sign in with your new password.',
      failed: 'Failed to change password. Check that your current password is correct.',
      policyFailed: 'New password must be 8-32 characters and include letters and numbers',
      sameAsCurrent: 'New password must differ from your current password',
      oidcOnlyDescription: 'Your account was created via OIDC sign-in and has no known local password yet.'
    }
  },
  tenantMember: {
    title: 'Members',
    loading: 'Loading members…',
    retry: 'Retry',
    permissions: {
      title: 'Role permissions',
      desc: 'What each role can do inside this workspace. Server-enforced; UI controls reflect the rules but are not the source of truth.'
    },
    role: {
      owner: 'Owner',
      admin: 'Admin',
      contributor: 'Contributor',
      viewer: 'Viewer'
    },
    leave: {
      confirmTitle: 'Leave this workspace?',
      confirmBody: 'You will lose access to all knowledge bases and agents in this workspace. You can be re-invited later.',
      confirm: 'Leave',
      success: 'You have left the workspace'
    },
    errors: {
      lastOwner: 'Cannot demote, remove, or leave as the last Owner. Promote another member to Owner first.',
      generic: 'Something went wrong. Please try again.'
    },
    audit: {
      action: {
        'rbac.member_added': 'Member added',
        'rbac.member_removed': 'Member removed',
        'rbac.member_role_changed': 'Role changed',
        'rbac.member_left': 'Member left',
        'rbac.access_denied': 'Access denied',
        'rbac.invitation_sent': 'Invitation sent',
        'rbac.invitation_accepted': 'Invitation accepted',
        'rbac.invitation_declined': 'Invitation declined',
        'rbac.invitation_revoked': 'Invitation revoked',
        'rbac.invitation_expired': 'Invitation expired'
      }
    }
  },
  tenantInvitation: {
    myInbox: {
      title: 'My invitations',
      description: 'Invitations from other workspaces. Accept to join with the assigned role.',
      empty: 'No pending invitations.',
      acceptButton: 'Accept',
      declineButton: 'Decline',
      acceptSuccess: 'Joined "{tenant}".',
      declineSuccess: 'Invitation declined.',
      from: 'From',
      tenantLabel: 'Workspace',
      expiresIn: 'Expires: {date}',
      messageLabel: 'Message'
    },
    errors: {
      notPending: 'The invitation is no longer pending.',
      forbidden: 'Only the invitee can accept or decline this invitation.',
      notFound: 'Invitation not found or already withdrawn.',
      generic: 'Something went wrong. Please try again.'
    }
  },
  imageAttr: {
    contain_text: {
      label: 'Text in the image',
      description: 'How much body text the picture itself carries. Decides whether reading its text is worth a separate OCR pass.',
      values: {
        none: {
          label: 'None',
          description: 'no text at all'
        },
        sparse: {
          label: 'Sparse',
          description: 'a few words — a logo, a road sign, a single label'
        },
        block: {
          label: 'Block',
          description: 'a block of body text — a screenshot, a table, a document page'
        }
      }
    },
    contain_data_visual: {
      label: 'Data visual',
      description: 'Whether the picture conveys data as a chart, graph, diagram or infographic. Such images keep their labels on the OCR path even when the text looks sparse.',
      values: {
        true: {
          label: 'Yes',
          description: 'a chart, graph or diagram with plotted values'
        },
        false: {
          label: 'No',
          description: 'a photo, drawing, icon or decoration'
        }
      }
    },
    layout_margin: {
      label: 'Non-text area',
      description: 'How much background surrounds the content. Large margins mean the page can be cropped tighter before OCR reads it.',
      values: {
        none: {
          label: 'None',
          description: 'the text reaches the edges'
        },
        small: {
          label: 'Small',
          description: 'a thin band of background'
        },
        large: {
          label: 'Large',
          description: 'plenty of non-text area: a desk, a room, a mostly empty page'
        }
      }
    },
    layout_upright: {
      label: 'Text orientation',
      description: 'Whether the text reads the right way up. A rotated or upside-down page is worth straightening before OCR reads it.',
      values: {
        true: {
          label: 'Upright',
          description: 'text reads in its normal orientation'
        },
        false: {
          label: 'Rotated',
          description: 'text is turned, tilted or upside down'
        }
      }
    }
  },
  imagePipeline: {
    errors: {
      noActionEnabled: 'Turn on at least one parsing action, otherwise nothing will be processed.'
    },
    default: {
      name: 'Manual',
      note_actions: {
        label: 'The two actions are independent',
        description: 'Each can be switched separately: with OCR off the image is still described, with caption off its text is still read. Only switching both off leaves an image untouched, which is why the panel refuses that combination.'
      },
      description: 'Turn the parsing actions on or off to fit the task.',
      caption_enabled: {
        label: 'Image caption',
        description: 'Ask the model for a one-line description of every image and store it as the caption.'
      },
      ocr_enabled: {
        label: 'OCR',
        description: 'Extract the text that appears in the image.'
      },
      caption: {
        thinking_enabled: {
          label: 'Caption with thinking',
          description: 'Let the model think before it writes the caption. In general you do not need thinking; enabling it makes parsing slower and may make the model overthink, so overly long reasoning can run past the limit and truncate the caption, failing the task. Only enable it when you have confirmed it is necessary.'
        }
      },
      ocr: {
        thinking_enabled: {
          label: 'OCR with thinking',
          description: 'Let the model think before it transcribes the text. In general you do not need thinking; enabling it makes parsing slower and may make the model overthink, so overly long reasoning can run past the limit and truncate the transcribed text, failing the task. Only enable it when you have confirmed it is necessary.'
        }
      }
    },
    smartocr: {
      ocr_on_unobserved: {
        label: 'Run OCR when image-attribute observation fails',
        description: 'When the model fails to observe the image attributes correctly, OCR runs by default so body text is never lost; turn off to skip. (A small vision model such as 4B, or custom image-instruction prompts that conflict with the system prompt, can cause the observation to fail; 8B and above rarely fail, so leaving this on is recommended)'
      },
      name: 'Smart',
      note_flow: {
        label: 'The observation decides',
        description: 'The image is described and observed first, and the attributes that come back decide whether OCR is worth a second pass. When they say the page needs straightening, it is straightened and its surroundings cropped before reading; when that step is unavailable or declines, the original photograph is read instead — never something worse.'
      },
      preprocess: {
        mode: {
          label: 'Document preprocessing',
          description: 'Off by default. Straightening and cropping before OCR adds processing time. Auto uses the observed attributes; Always tries preprocessing for every image selected for OCR. Busy or resource-limited requests use the original image.',
          options: {
            auto: 'Auto',
            off: 'Off',
            always: 'Always'
          }
        }
      },
      observation: {
        thinking_enabled: {
          label: 'Describe with thinking',
          description: 'Let the model think before it describes the image and reports its attributes. In general you do not need thinking; enabling it makes parsing slower and may make the model overthink, so overly long reasoning can run past the limit and truncate the description, failing the task. Only enable it when you have confirmed it is necessary.'
        }
      },
      ocr: {
        thinking_enabled: {
          label: 'Text recognition with thinking',
          description: 'Let the model think before it transcribes the text. In general you do not need thinking; enabling it makes parsing slower and may make the model overthink, so overly long reasoning can run past the limit and truncate the transcribed text, failing the task. Only enable it when you have confirmed it is necessary.'
        }
      },
      description: 'Observe the image attributes and describe the image first, then decide from the attributes whether to run OCR, saving model calls and speeding up parsing. When the image is recognised as a photograph of a correctable page or label, it is straightened and cropped before recognition to improve OCR accuracy; if that fails, the original image is used.'
    }
  },
  memorySettings: {
    usage: {
      title: 'When memories are used'
    },
    kinds: {
      profile: 'About you',
      preference: 'Preference',
      fact: 'Fact',
      task: 'Ongoing task',
      interest: 'Long-term interest'
    }
  }
}
