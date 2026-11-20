export default {
  memorySettings: {
    kinds: {
      profile: '个人信息',
      preference: '偏好',
      fact: '事实',
      task: '在办事项',
      interest: '长期关注'
    },
    usage: {
      title: '记忆何时会被使用'
    }
  },
  imagePipeline: {
    smartocr: {
      name: '智能模式',
      description: '先观察图片特征并进行图片描述，再根据图片特征决定是否调用OCR对图片进行识别，以节省模型调用次数并提升解析速度。当识别到图片为可校正的文档或标签页照片时，会在识别前自动摆正并裁剪页面，以提升 OCR 准确率；若校正失败则直接使用原图。',
      ocr: {
        thinking_enabled: {
          label: '文字识别时开启思考',
          description: '让模型在提取文字前先思考。一般情况下不需要开启思考，开启之后不仅更慢，还可能造成大模型思考内容过长截断正文输出造成任务失败。请仅在确认有必要的情况下开启。'
        }
      },
      observation: {
        thinking_enabled: {
          label: '描述时开启思考',
          description: '让模型在描述图片并观察属性前先思考。一般情况下不需要开启思考，开启之后不仅更慢，还可能造成大模型思考内容过长截断正文输出造成任务失败。请仅在确认有必要的情况下开启。'
        }
      },
      preprocess: {
        mode: {
          label: '文档预处理',
          description: '默认关闭。开启后，会在 OCR 前摆正并裁剪页面，增加处理耗时。自动：按观察结果判断；总是：对进入 OCR 的图片都尝试预处理；繁忙或超限时使用原图。',
          options: {
            auto: '自动',
            off: '关闭',
            always: '总是'
          }
        }
      },
      note_flow: {
        label: '由观察结果决定',
        description: '先描述图片并观察属性，由属性决定是否值得再为它花一次 OCR。属性显示页面需要摆正时，会先摆正并裁掉周围环境再识别；若该步骤不可用或判定不适用，则直接用原图，绝不会比不启用更差。'
      },
      ocr_on_unobserved: {
        label: '图片属性观察失败时仍执行 OCR',
        description: '当模型未能正确观察到图片属性时，默认仍执行 OCR 兜底，以免漏掉正文文字；关闭则跳过。（采用 4B 等小参数视觉模型，或自定义的图片解析提示词与系统提示词冲突时，可能造成观察失败；8B 及以上模型的失败概率很低，不建议关闭）'
      }
    },
    default: {
      name: '传统',
      description: '用户根据任务需要手动选择解析动作开关。',
      ocr: {
        thinking_enabled: {
          label: '文字识别时开启思考',
          description: '让模型在提取文字前先思考。一般情况下不需要开启思考，开启之后不仅更慢，还可能造成大模型思考内容过长截断正文输出造成任务失败。请仅在确认有必要的情况下开启。'
        }
      },
      caption: {
        thinking_enabled: {
          label: '图片描述时开启思考',
          description: '让模型在写描述前先思考。一般情况下不需要开启思考，开启之后不仅更慢，还可能造成大模型思考内容过长截断正文输出造成任务失败。请仅在确认有必要的情况下开启。'
        }
      },
      ocr_enabled: {
        label: '文字识别',
        description: '提取图片中出现的文字。'
      },
      caption_enabled: {
        label: '图片描述',
        description: '让模型为每张图片生成一句内容描述，作为图片的说明文字。'
      },
      note_actions: {
        label: '两项动作互相独立',
        description: '两项各自开关：关掉识别，图片仍会被描述；关掉描述，文字仍会被识别。只有两个都关掉时这张图才不会被处理 —— 所以面板不允许这种组合。'
      }
    },
    errors: {
      noActionEnabled: '至少开启一个解析动作，否则多模态不会处理任何内容。'
    }
  },
  imageAttr: {
    layout_upright: {
      label: '文字朝向',
      description: '图中文字是否正立。歪斜或倒置的页面，值得在 OCR 之前摆正。',
      values: {
        false: {
          label: '非正立',
          description: '文字被旋转、倾斜拍摄或倒置'
        },
        true: {
          label: '正立',
          description: '文字方向正常'
        }
      }
    },
    layout_margin: {
      label: '版面留白',
      description: '文字内容之外的部分（桌面、背景、空白）占整张画面的比例。留白大意味着可以在 OCR 之前把页面裁得更紧。',
      values: {
        large: {
          label: '大片留白',
          description: '有大片非文字区域 —— 桌面、房间，或拍进来的周边环境'
        },
        small: {
          label: '少量留白',
          description: '边缘只有一条窄边'
        },
        none: {
          label: '无留白',
          description: '文字几乎铺满画面'
        }
      }
    },
    contain_data_visual: {
      label: '数据可视化',
      description: '图片是否以图表、曲线、示意图或信息图的方式承载数据；这类图即使看起来文字很少，也会保留在 OCR 路径上。',
      values: {
        false: {
          label: '否',
          description: '否 —— 照片、插画、图标或装饰图'
        },
        true: {
          label: '是',
          description: '是 —— 图表、曲线或示意图'
        }
      }
    },
    contain_text: {
      label: '图中文字量',
      description: '图片自身承载多少正文文字，决定是否值得为它单独跑一轮 OCR。',
      values: {
        block: {
          label: '成段正文',
          description: '成段正文 —— 截图、表格、文档页面'
        },
        sparse: {
          label: '少量文字',
          description: '只有少量文字 —— 图标、路牌、单个标签'
        },
        none: {
          label: '无文字',
          description: '完全没有文字'
        }
      }
    }
  },
  tenantInvitation: {
    errors: {
      notPending: '邀请已不在待处理状态。',
      forbidden: '只有被邀请人本人可以接受或拒绝该邀请。',
      notFound: '邀请不存在或已被撤销。',
      generic: '操作失败，请稍后重试。'
    },
    myInbox: {
      title: '我的邀请',
      description: '其他空间发给您的加入邀请。接受后您将以对应角色加入对方空间。',
      empty: '没有待处理的邀请。',
      acceptButton: '接受',
      declineButton: '拒绝',
      acceptSuccess: '已加入 "{tenant}"。',
      declineSuccess: '已拒绝邀请。',
      from: '邀请人',
      tenantLabel: '空间',
      expiresIn: '到期：{date}',
      messageLabel: '留言'
    }
  },
  tenantMember: {
    title: '成员管理',
    loading: '正在加载成员…',
    retry: '重试',
    audit: {
      action: {
        'rbac.member_added': '新增成员',
        'rbac.member_removed': '移除成员',
        'rbac.member_role_changed': '角色变更',
        'rbac.member_left': '成员退出',
        'rbac.access_denied': '访问被拒',
        'rbac.invitation_sent': '发出邀请',
        'rbac.invitation_accepted': '接受邀请',
        'rbac.invitation_declined': '拒绝邀请',
        'rbac.invitation_revoked': '撤销邀请',
        'rbac.invitation_expired': '邀请过期'
      }
    },
    errors: {
      lastOwner: '无法降级、移除或退出最后一位 Owner，请先把其他成员提升为 Owner。',
      generic: '操作失败，请稍后重试。'
    },
    leave: {
      confirmTitle: '确认退出当前空间？',
      confirmBody: '退出后您将无法访问当前空间内的所有知识库和智能体。后续可被再次邀请加入。',
      confirm: '退出',
      success: '已退出当前空间'
    },
    role: {
      owner: '所有者',
      admin: '管理员',
      contributor: '编辑',
      viewer: '访客'
    },
    permissions: {
      title: '角色权限说明',
      desc: '每个角色在当前空间内能做的事情。服务端强制执行，UI 控件仅作展示。'
    }
  },
  userProfile: {
    title: '用户信息',
    description: '查看您的账户基础信息（用户 ID、用户名、账号、注册时间），并可修改登录密码',
    changePassword: {
      label: '修改密码',
      description: '使用当前密码验证后设置新密码。修改成功后所有设备上的登录状态将失效，需要重新登录。',
      currentLabel: '当前密码',
      currentPlaceholder: '请输入当前密码',
      currentRequired: '请输入当前密码',
      newLabel: '新密码',
      newPlaceholder: '请输入新密码',
      confirmLabel: '确认新密码',
      confirmPlaceholder: '再次输入新密码',
      submit: '更新密码',
      success: '密码已更新，请使用新密码重新登录',
      failed: '修改密码失败，请检查当前密码是否正确',
      policyFailed: '新密码须为 8-32 个字符，且同时包含字母和数字',
      sameAsCurrent: '新密码不能与当前密码相同',
      oidcOnlyDescription: '您的账号通过 OIDC 登录开通，尚未设置本地登录密码。'
    }
  },
  credential: {
    configured: '已配置',
    unconfigured: '未配置',
    configure: '配置',
    update: '更换',
    remove: '移除',
    inputPlaceholder: '请输入',
    savedToast: '凭据已保存',
    saveFailed: '保存凭据失败',
    removedToast: '凭据已移除',
    removeFailed: '移除凭据失败',
    confirmRemovePrompt: '确认移除？此操作不可撤销',
    confirmRemove: '确认移除'
  },
  integrations: {
    claw: {
      title: 'WeKnora Skill'
    },
    chrome: {
      title: '知识管理助手'
    },
    agentEditor: {
      desc: '将智能体发布到 IM 平台或网站，在集成中心统一管理'
    },
    embedOverview: {
      title: '网页嵌入渠道'
    },
    imOverview: {
      title: '已接入的 IM'
    },
    api: {
      title: 'API 集成',
      updateApiKeyScopeFailed: '更新 API Key 失败'
    },
    tabs: {
      im: 'IM 集成',
      embed: '网页嵌入',
      api: 'API 集成',
      chrome: 'Chrome 插件',
      cli: 'CLI',
      claw: 'Claw Skill',
      mcpserver: 'MCP Server'
    },
    mcpserver: {
      title: 'MCP Server',
      tools: {
        list_knowledge_bases: '列出知识库',
        list_knowledge_basesDesc: '返回端点范围内的知识库及其支持的检索方式',
        search_knowledge: '语义搜索',
        search_knowledgeDesc: '按自然语言问题在知识库中检索相关片段并附来源',
        grep_chunks: '关键词/正则搜索',
        grep_chunksDesc: '对原始分块做大小写不敏感的正则匹配，适合精确词、编号、代码',
        list_documents: '列出文档',
        list_documentsDesc: '分页列出某个知识库下的文档',
        read_document: '阅读文档',
        read_documentDesc: '按顺序读取文档的元信息和分块内容',
        ask: '问答',
        askDesc: '运行端点配置的默认 Agent，返回带引用的完整回答，支持多轮续聊',
        wiki_search: '搜索 Wiki',
        wiki_searchDesc: '在知识库生成的 Wiki 页面中搜索',
        wiki_read_page: '读取 Wiki 页面',
        wiki_read_pageDesc: '按 slug 读取一篇 Wiki 页面',
        wiki_index: '浏览 Wiki 目录',
        wiki_indexDesc: '查看某个知识库 Wiki 的目录结构',
        add_document: '新增文档',
        add_documentDesc: '用 Markdown 文本或 URL 向知识库添加文档',
        update_document: '更新文档',
        update_documentDesc: '替换 Markdown 文档的内容或标题',
        delete_document: '删除文档',
        delete_documentDesc: '永久删除文档及其索引数据'
      },
      groups: {
        retrieve: '检索与阅读',
        chat: '问答',
        wiki: 'Wiki',
        ingest: '写入（谨慎开启）'
      }
    },
    cli: {
      title: 'WeKnora CLI'
    }
  },
  datasource: {
    title: '数据源管理',
    description: '配置外部数据源，自动同步内容到知识库',
    add: '添加数据源',
    empty: '暂无数据源',
    edit: '编辑',
    delete: '删除',
    deleteConfirm: '确定删除该数据源？同步的知识不会被删除。',
    deleteSuccess: '数据源已删除',
    deleteFailed: '删除失败',
    syncNow: '立即同步',
    syncTriggered: '同步任务已提交',
    syncFailed: '同步触发失败',
    pause: '暂停',
    resume: '恢复',
    paused: '已暂停',
    resumed: '已恢复',
    pauseFailed: '暂停失败',
    logs: '日志',
    syncModeLabel: '同步模式',
    parseModeLabel: '解析模式',
    parseModeHint: '飞书云文档的解析方式。块级解析更快并保留文档内附件；导出解析将文档导出为 docx 后解析，图片与文档的关联更完整。',
    createTitle: '添加数据源',
    editTitle: '编辑数据源',
    nameLabel: '名称',
    namePlaceholder: '输入数据源名称',
    sectionBasic: '基本信息',
    testConnection: '测试连接',
    testSuccess: '连接成功',
    testFailed: '连接失败',
    connected: '已连接',
    connectionFailed: '连接失败',
    isRequired: '为必填项',
    credentialsLabel: '凭证',
    resourceHint: '选择要同步的内容空间/文件夹',
    untitled: '无标题',
    resourceLoadFailed: '加载资源列表失败',
    noResources: '未找到可同步的知识库空间',
    noResourcesDesc: '应用需要通过群聊获得知识库访问权限才能拉取内容',
    noResourcesDesc_notion: '应用需要获得 Notion 页面的访问权限才能拉取内容',
    retryLoadResources: '重新加载',
    guideStep1: '在飞书中创建一个群聊，在群设置「群机器人」中添加你的应用',
    guideStep2: '打开知识库「设置」→「成员设置」→ 添加成员，搜索该群聊名称并添加',
    guideStep3: '确保群聊角色至少为「可阅读」，然后回到这里点重新加载',
    guideStep1_notion: '在 Notion 中打开你想要同步的页面或数据库',
    guideStep2_notion: '点击右上角的「···」菜单，选择「Connect to」或「Add connections」',
    guideStep3_notion: '搜索并选择你的集成应用（Integration），然后回到这里点重新加载',
    noResourcesDesc_nextcloud: '未找到可访问的目录或支持的文件',
    guideStep1_nextcloud: '登录 Nextcloud，确认账号有权读取所选目录',
    guideStep2_nextcloud: '在「个人设置 → 安全 → 设备和会话」中创建应用密码',
    guideStep3_nextcloud: '在这里替换凭据，然后重新加载资源',
    noResourcesDesc_seafile: '该令牌能访问的资料库为空，或全部为加密资料库（不支持同步）',
    guideStep1_seafile: '登录 Seafile，确认账号至少拥有一个未加密资料库的读取权限',
    guideStep2_seafile: '在「设置 → Web API 令牌」中生成或重新生成令牌',
    guideStep3_seafile: '回到这里填入新令牌并点重新加载',
    permissionDocLink: '查看飞书知识库权限配置文档',
    syncScheduleLabel: '同步频率',
    conflictLabel: '冲突策略',
    syncDeletions: '同步删除（源端删除时同步删除知识库中的条目）',
    createAndSync: '创建并立即同步',
    createAndSyncSuccess: '数据源创建成功，同步任务已提交',
    createButSyncFailed: '数据源已创建，但触发同步失败',
    updateSuccessSyncHint: '数据源更新成功；编辑不会自动触发同步，如需重新导入请点击“同步”。',
    saveFailed: '保存失败',
    syncHistory: '同步历史',
    refreshLogs: '刷新日志',
    noLogs: '暂无同步记录',
    comingSoon: '即将支持',
    docHint: '在以下地址获取凭证：',
    openDoc: '打开文档',
    prereqBarText: '首次使用？点击查看飞书应用配置指引',
    prereqBarText_yuque: '首次使用？点击查看语雀 Token 配置指引',
    prereqStep1Brief_yuque: '创建语雀个人 Token',
    prereqStep1Desc_yuque: '登录语雀 → 个人头像 → 设置 → Token → 新建 Token',
    prereqStep2Brief_yuque: '为 Token 勾选所需权限',
    prereqStep2Desc_yuque: '至少勾选 repo:read 和 doc:read（读取知识库和文档内容）',
    prereqStep3Brief_yuque: '（可选）企业版填写 Base URL',
    prereqStep3Desc_yuque: '公有云用户无需填写；语雀企业版或私有部署请填写企业域名',
    prereqStep1Brief_feishu: '创建飞书自建应用',
    prereqStep1Desc_feishu: '登录飞书开放平台 → 创建企业自建应用',
    prereqStep2Brief_feishu: '添加机器人能力',
    prereqStep2Desc_feishu: '开放平台 → 你的应用 → 添加应用能力 → 机器人',
    prereqStep3Brief_feishu: '配置应用权限',
    prereqStep3Desc_feishu: '为应用开通 wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly 权限',
    prereqStep1Brief_lark: '创建 Lark 自建应用',
    prereqStep1Desc_lark: '登录 Lark 开放平台 → 创建企业自建应用',
    prereqStep2Brief_lark: '添加机器人能力',
    prereqStep2Desc_lark: '开放平台 → 你的应用 → 添加应用能力 → 机器人',
    prereqStep3Brief_lark: '配置应用权限',
    prereqStep3Desc_lark: '为应用开通 wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly 权限',
    prereqStep1Brief_feishu_drive: '创建飞书自建应用',
    prereqStep1Desc_feishu_drive: '登录飞书开放平台 → 创建企业自建应用',
    prereqStep2Brief_feishu_drive: '添加机器人能力',
    prereqStep2Desc_feishu_drive: '开放平台 → 你的应用 → 添加应用能力 → 机器人',
    prereqStep3Brief_feishu_drive: '配置应用权限',
    prereqStep3Desc_feishu_drive: '为应用开通 drive:drive:readonly, drive:export:readonly, docx:document:readonly 权限',
    prereqStep1Brief_lark_drive: '创建 Lark 自建应用',
    prereqStep1Desc_lark_drive: '登录 Lark 开放平台 → 创建企业自建应用',
    prereqStep2Brief_lark_drive: '添加机器人能力',
    prereqStep2Desc_lark_drive: '开放平台 → 你的应用 → 添加应用能力 → 机器人',
    prereqStep3Brief_lark_drive: '配置应用权限',
    prereqStep3Desc_lark_drive: '为应用开通 drive:drive:readonly, drive:export:readonly, docx:document:readonly 权限',
    prereqOpenConsole_yuque: '前往语雀 Token 设置',
    yuqueFolderModeLabel: '目录结构',
    yuqueFolderModeToc: '按语雀目录分层',
    yuqueFolderModeNone: '平铺在根目录',
    yuqueFolderModeHint: '按语雀的目录层级放置文档。注意：之后在知识库里手动调整的目录，会在该文档下次同步时被覆盖回语雀的结构。',
    yuqueTOCOnly: '只同步语雀目录中可见的文档',
    yuqueTOCOnlyHint: '需要先选择「按语雀目录分层」。已经同步进知识库的文档不受影响——语雀中不在目录里的文档只是不再新增，不会被删除。',
    dingtalkIngestLabel: '钉钉摄取范围',
    dingtalkIncludeUploadedFiles: '摄取知识库中的上传文件（docx / pptx / xlsx / pdf）',
    dingtalkIncludeUploadedFilesHint: '默认关闭。开启后，所选范围内的 Word / PowerPoint / Excel / PDF 上传文件会被下载并解析入库，单个文件上限 64 MiB；这些文件的正文会计入存储与向量化成本。关闭时它们只是被跳过，同步日志会说明开关未开启，不会删除知识库中已有的副本。',
    prereqBarText_dingtalk: '首次使用？点击查看钉钉应用配置指引',
    prereqStep1Brief_dingtalk: '创建企业内部应用',
    prereqStep1Desc_dingtalk: '在钉钉开放平台创建企业内部应用，并获取 Client ID 和 Client Secret',
    prereqStep2Brief_dingtalk: '开通知识库读取权限',
    prereqStep2Desc_dingtalk: '开通 Wiki.Workspace.Read、Wiki.Node.Read 和 Storage.File.Read',
    prereqStep3Brief_dingtalk: '填写操作人 Union ID',
    prereqStep3Desc_dingtalk: '填写有权访问目标知识库的钉钉用户 Union ID',
    prereqOpenConsole_dingtalk: '前往钉钉开放平台配置',
    prereqBarText_ima: '首次使用？点击查看腾讯 IMA OpenAPI 授权指引',
    prereqStep1Brief_ima: '开通 IMA 智能体接入',
    prereqStep1Desc_ima: '登录 https://ima.qq.com/agent-interface 并申请 OpenAPI 接入',
    prereqStep2Brief_ima: '获取 ClientID 与 APIKey',
    prereqStep2Desc_ima: '在智能体接入页复制 ima-openapi-clientid 与 ima-openapi-apikey 两个凭证',
    prereqStep3Brief_ima: '授权目标知识库',
    prereqStep3Desc_ima: '在 IMA 客户端为该凭证授权需要同步的知识库，未授权的知识库不会出现在列表中',
    prereqOpenConsole_ima: '前往 IMA OpenAPI 控制台',
    prereqBotBrief: '为应用添加「机器人」能力',
    prereqBotDesc: '开放平台 → 添加应用能力 → 机器人 → 创建版本并发布',
    prereqPermBrief: '开通 API 权限',
    prereqOpenConsole: '前往飞书开放平台配置',
    prereqMemberBrief: '通过群聊添加为知识库成员',
    prereqMemberDesc: '创建群聊 → 添加应用为群机器人 → 将群聊添加为知识库成员',
    back: '上一步',
    next: '下一步',
    save: '保存',
    schedule30min: '每 30 分钟',
    schedule1h: '每小时',
    schedule6h: '每 6 小时',
    schedule12h: '每 12 小时',
    schedule24h: '每天',
    neverSynced: '未同步',
    justNow: '刚刚',
    minutesAgo: '{n} 分钟前',
    hoursAgo: '{n} 小时前',
    daysAgo: '{n} 天前',
    syncError: {
      dingtalk_document_failed: '无法读取钉钉文档，请检查访问权限后重试同步。',
      dingtalk_document_too_large: '钉钉文件超过 64 MiB 下载上限，本次已跳过，请压缩或拆分后再同步。',
      dingtalk_resource_failed: '钉钉资源不可用，请检查访问权限和已选资源后重试。',
      deletion_lookup_failed: '删除前查找文档失败，请查看服务器日志',
      deletion_failed: '删除失败，请查看服务器日志',
      ingest_failed: '导入失败，请查看服务器日志',
      nextcloud_permission_denied: '无权访问该 Nextcloud 文件，请检查账号权限。',
      nextcloud_not_found: 'Nextcloud 文件在扫描后消失，下次同步将重试。',
      nextcloud_file_too_large: 'Nextcloud 文件超过 MAX_FILE_SIZE_MB 限制。',
      nextcloud_empty_file: 'Nextcloud 文件内容为空，已跳过。',
      nextcloud_source_changed: 'Nextcloud 文件在下载过程中发生变化，下次同步将重试。',
      nextcloud_invalid_response: 'Nextcloud 返回了无效或不完整的 WebDAV 响应。',
      nextcloud_ssrf_blocked: 'Nextcloud 请求被 SSRF 策略拦截，请检查 SSRF_WHITELIST。',
      nextcloud_fetch_failed: '从 Nextcloud 获取文件失败，下次同步将重试。',
      seafile_permission_denied: '无权访问该 Seafile 文件，请检查令牌所属账号的资料库权限。',
      seafile_not_found: 'Seafile 文件不存在或已被移动，下次同步将重试。',
      seafile_file_too_large: 'Seafile 文件超过大小限制，请调大 MAX_FILE_SIZE_MB 或缩小该文件。',
      seafile_empty_file: 'Seafile 文件内容为空，已跳过。',
      seafile_source_changed: 'Seafile 文件在获取过程中发生变化，下次同步将重试。',
      seafile_invalid_response: 'Seafile 返回了无法解析的响应，请检查服务器版本与反向代理配置。',
      seafile_ssrf_blocked: 'Seafile 文件下载地址被 SSRF 策略拦截，请将 fileserver 域名加入 SSRF_WHITELIST。',
      seafile_fetch_failed: '从 Seafile 获取文件失败，下次同步将重试。'
    },
    resourceType: {
      wikiSpace: '知识库空间',
      docCategory: '文档标签',
      book: '语雀知识库',
      library: 'Seafile 资料库'
    },
    scheduleHuman: {
      '30min': '每 30 分钟',
      '1h': '每小时',
      '6h': '每 6 小时',
      '12h': '每 12 小时',
      '24h': '每天'
    },
    confluence: {
      cloudFolderLimitation: 'Confluence Cloud 暂不支持在此列出空间顶层文件夹等容器下的页面；选择整个空间仍会同步它们。'
    },
    field: {
      appId: 'App ID',
      appSecret: 'App Secret',
      clientId: 'Client ID',
      clientSecret: 'Client Secret',
      operatorId: '操作人 Union ID',
      operatorIdHint: '用于按该用户的权限读取知识库，可通过钉钉“查询用户详情”接口获取',
      integrationToken: 'Integration Token',
      apiToken: 'API Token',
      confluenceEdition: 'Confluence 版本',
      confluenceEditionServer: 'Server / Data Center',
      confluenceEditionCloud: 'Cloud',
      confluenceBaseUrl: 'Confluence 地址',
      confluenceUsername: '用户名或邮箱',
      confluencePat: 'Server/DC 个人访问令牌（PAT）',
      confluencePatHint: '选填。填写后使用 Bearer 认证，无需用户名和密码。',
      confluencePassword: 'Server/DC 密码',
      confluenceApiToken: 'Cloud API 令牌',
      imaClientId: 'IMA ClientID',
      imaApiKey: 'IMA APIKey',
      baseUrl: 'Base URL（可选）',
      baseUrlHint: '留空将使用默认公有云地址；如果是私有部署/企业内网部署，或需要通过反向代理访问，请填写自定义地址（例如 https://api-proxy.example.com）',
      feedUrls: '订阅源地址',
      feedUrlsHint: '每行一个 RSS / Atom 订阅源地址，支持同时填写多个',
      authHeaders: '自定义请求头（可选）',
      authHeadersHint: '用于访问私有订阅源，每行一个，格式为「名称: 值」，例如 Authorization: Bearer xxxx'
    },
    drive: {
      folderTokenLabel: '云盘文件夹 Token',
      folderTokenPlaceholder: '输入 folder_token 或飞书云盘文件夹链接',
      folderTokenRequired: '请输入具体文件夹的 folder_token，不支持云空间根目录',
      rootNotSupportedHint: '根目录不分页且不返回快捷方式，请选择具体文件夹',
      load: '加载',
      shareHint: '需先将该云盘文件夹分享给应用所在的群，应用才能访问',
      placeholderTitle: '请先加载云盘文件夹',
      placeholderDesc: '在上方输入 folder_token（或从飞书云盘文件夹 URL 复制）并点击「加载」',
      loadForbiddenHint: '应用无权访问该文件夹。请在飞书云盘中将该文件夹分享给应用所在的群后再试。',
      loadAuthHint: '应用凭证无效或缺少云盘权限，请检查 App ID / App Secret 及 drive:drive:readonly 等权限。',
      loadNotFoundHint: 'folder_token 不存在或已删除，请确认从飞书云盘文件夹 URL 复制的 token 正确。'
    },
    connectorDesc: {
      feishu: '同步飞书知识库中的文档、表格、文件',
      lark: '同步 Lark 知识库中的文档、表格、文件（飞书国际版）',
      feishu_drive: '同步飞书云盘文件夹中的文档、表格、文件',
      lark_drive: '同步 Lark 云盘文件夹中的文档、表格、文件（飞书国际版）',
      notion: '同步 Notion 中的页面和数据库',
      confluence: '将 Confluence 空间和页面同步为 Markdown',
      yuque: '同步语雀知识库中的文档',
      dingtalk: '同步钉钉知识库中的在线文档',
      rss: '同步 RSS / Atom 订阅源中的文章',
      ima: '同步腾讯 IMA 知识库中的文档、笔记与文件（暂不支持 AI 会话与视频解析）',
      gitlab: '同步 GitLab 项目中的文件',
      nextcloud: '通过 WebDAV 同步 Nextcloud 中的目录与文件',
      seafile: '同步 Seafile 资料库中的目录与文件'
    },
    connector: {
      feishu: '飞书',
      lark: 'Lark（飞书国际版）',
      feishu_drive: '飞书云盘',
      lark_drive: 'Lark 云盘',
      notion: 'Notion',
      confluence: 'Confluence',
      yuque: '语雀',
      dingtalk: '钉钉文档',
      rss: 'RSS / Atom 订阅',
      ima: '腾讯 IMA',
      gitlab: 'GitLab',
      nextcloud: 'Nextcloud',
      seafile: 'Seafile'
    },
    logDetail: {
      startTime: '开始时间',
      endTime: '结束时间',
      failedItems: '失败文档',
      failedItemsMore: '还有 {n} 个失败文档未显示',
      docsFailedSummary: '{n} 个文档同步失败'
    },
    logSummary: {
      total: '总次数',
      success: '成功',
      failed: '失败',
      items: '同步条目'
    },
    logMetric: {
      total: '总计',
      skipped: '跳过',
      failed: '失败'
    },
    logStatus: {
      running: '同步中',
      success: '成功',
      partial: '部分成功',
      failed: '失败',
      canceled: '已取消'
    },
    step: {
      selectType: '选择类型',
      credentials: '配置凭证',
      resources: '选择范围',
      strategy: '同步策略'
    },
    conflict: {
      overwrite: '覆盖更新',
      skip: '跳过已存在'
    },
    seafile: {
      baseUrl: 'Seafile 地址',
      apiToken: 'API 令牌',
      apiTokenHint: '在 Seafile「设置 → Web API 令牌」中生成；账号对所选资料库有读权限即可，令牌不会随文件下载请求发送。',
      singleLibraryOnly: '一个数据源只能同步一个资料库，请先取消已选资料库中的内容再改选。',
      selectionRequired: '请至少勾选一个资料库、目录或文件'
    },
    nextcloud: {
      baseUrl: 'Nextcloud 地址',
      baseUrlHint: '填写安装地址，如 https://nextcloud.example.com/cloud，不含 /remote.php/dav。私网部署请使用现有的 SSRF_WHITELIST 配置。',
      username: '用户名',
      appPassword: '应用密码',
      appPasswordHint: '在「个人设置 → 安全 → 设备和会话」中创建应用密码，使用生成的用户名和应用密码。',
      selectionRequired: '请至少选择一个目录或文件',
      includeExtensions: '包含的扩展名（可选）',
      excludeExtensions: '排除的扩展名（可选）',
      extensionsHint: '用逗号分隔扩展名，如 .pdf, .md。包含项留空表示所有支持的格式，排除项优先。修改过滤条件也会改变删除对账范围。'
    },
    gitlab: {
      baseUrl: 'GitLab 地址',
      accessToken: '个人访问令牌',
      projects: 'GitLab 项目',
      projectsHint: '填写项目 ID 或命名空间路径（如 group/project），可选指定分支和目录。',
      project: '项目',
      projectId: '项目 ID',
      projectIdPlaceholder: '例如：12345 或 group/project',
      ref: '分支',
      refPlaceholder: '留空时使用默认分支',
      paths: '同步目录',
      pathsPlaceholder: '每行一个目录；留空同步整个项目',
      addProject: '添加项目',
      projectRequired: '请至少添加一个 GitLab 项目'
    },
    status: {
      active: '已连接',
      paused: '已暂停',
      error: '异常'
    },
    syncMode: {
      incremental: '增量同步',
      full: '全量同步'
    },
    parseMode: {
      inherit: '使用服务器配置',
      blocks: '块级解析（默认）',
      export: '导出解析（docx）'
    }
  },
  mermaid: {
    diagram: '图表',
    expand: '全屏查看',
    zoomIn: '放大',
    zoomOut: '缩小',
    reset: '重置',
    download: '下载图片',
    close: '关闭',
    downloading: '下载中...'
  },
  agentEditor: {
    builtinHint: '这是内置智能体，名称和描述不可修改，但可以调整配置参数',
    fileTypes: {
      label: '支持的文件类型',
      desc: '限制可选择的文件类型，留空表示支持所有类型',
      allTypes: '全部类型',
      pdf: 'PDF 文档',
      word: 'Word 文档 (.docx/.doc)',
      textLabel: '文本',
      text: '纯文本文件 (.txt)',
      markdown: 'Markdown 文档',
      csv: '逗号分隔值文件',
      excel: 'Excel 表格 (.xlsx/.xls)',
      imageLabel: '图片',
      image: '图片文件 (.jpg/.jpeg/.png)'
    },
    fallback: {
      fixed: '固定回复',
      model: '模型生成'
    },
    faq: {
      title: 'FAQ 优先策略'
    },
    chatParser: {
      label: '聊天附件解析策略',
      desc: '为不同文件类型指定解析引擎，仅对当前智能体的聊天附件生效',
      waitTimeoutLabel: '附件解析等待超时（秒）',
      waitTimeoutDesc: '单轮问答等待附件解析完成的最长时间，超时后未完成的附件会被跳过。大文件 / 扫描件可调大。0 表示使用全局默认。'
    },
    audioUpload: {
      label: '语音上传',
      desc: '启用后用户可在对话中上传音频文件，系统将使用 ASR 模型自动转录为文字',
      asrModel: 'ASR 模型',
      asrModelDesc: '用于音频转录的语音识别模型，未配置时音频文件将以占位符形式传递',
      asrModelPlaceholder: '请选择 ASR 模型'
    },
    imageUpload: {
      navLabel: '附件上传',
      sectionTitle: '附件上传',
      sectionDesc: '配置对话中图片、文档、音频等附件的上传、解析及对应模型',
      label: '图片上传',
      desc: '启用后用户可在对话中上传图片并由 VLM 理解',
      vlmModel: 'VLM 模型',
      vlmModelDesc: '用于图片分析的视觉语言模型',
      vlmModelPlaceholder: '请选择 VLM 模型',
      vlmModelRequired: '启用图片上传时必须选择 VLM 模型',
      imageUnderstandingLabel: '附件图片理解 / 扫描件 OCR',
      imageUnderstandingDesc: '对图片型 PDF/PPT 等扫描件，当解析不出文字时用 VLM 进行 OCR 识别。开启会增加解析耗时，默认关闭。',
      ocrMaxPagesLabel: '扫描件 OCR 最大页数',
      ocrMaxPagesDesc: '扫描件送入 VLM 做 OCR 的最大页数，越多覆盖越全但越慢、越贵。0 表示使用全局默认。',
      useGlobalDefault: '0 = 全局默认',
      storageProvider: '图片存储',
      storageProviderDesc: '选择图片文件的存储引擎，留空则使用系统默认',
      storageProviderPlaceholder: '选择存储引擎',
      storageDefault: '系统默认',
      notConfigured: '未配置',
      goStorageSettings: '去存储设置中配置'
    },
    llmCallTimeout: {
      label: 'LLM 调用超时',
      desc: '模型客户端的请求超时配置（秒）；流式响应持续输出时，总时长可能超过此值。',
      hint: '留空或填 0 表示使用默认值（120 秒）',
      placeholder: '输入秒数，建议范围 60-1800'
    },
    mcp: {
      label: 'MCP 服务',
      desc: '选择 Agent 可以调用的 MCP 服务',
      selectLabel: '选择 MCP 服务',
      selectDesc: '选择要启用的 MCP 服务',
      selectPlaceholder: '选择 MCP 服务',
      authWaitTimeout: '授权等待超时（秒）',
      authWaitTimeoutDesc: '对话中触发 OAuth 授权时，等待你完成授权的最长秒数，超时后自动跳过授权提示（仅对使用 OAuth 的 MCP 服务生效）。',
      authWaitTimeoutPlaceholder: '默认 600 秒',
      accessLevel: '执行权限上限',
      accessLevelDesc: '修改数据的工具（MCP 工具、Wiki 写入）能否直接执行：只读时不提供这类工具，修改前确认时每次先征求你同意。被标记为需要审批的 MCP 工具始终需要确认。',
      unavailableService: '不可用服务'
    },
    agentType: {
      label: '智能体类型',
      desc: '选择一个预设会自动填充系统提示词、工具列表和推荐的知识库范围。',
      defaultNamePattern: '我的{label}',
      kbIncompatibleWarn: '已选的 {count} 个知识库不适用于当前类型，请手动调整',
      kbMismatch: {
        ragQa: '未启用 RAG 检索',
        wikiQa: '未启用 Wiki',
        hybridRagWiki: '未启用任何检索能力',
        dataAnalysis: '需启用 RAG（不支持 FAQ）',
        quickAnswer: '快速问答模式需启用 RAG 检索',
        generic: '不适用于当前类型'
      }
    },
    im: {
      title: 'IM 集成',
      description: '将智能体接入即时通讯平台，支持企业微信、飞书、Slack、Telegram、钉钉、Mattermost、微信、QQBot 和云之家',
      feishu: '飞书',
      lark: 'Lark（飞书国际版）',
      slack: 'Slack',
      telegram: 'Telegram',
      dingtalk: '钉钉',
      mattermost: 'Mattermost',
      wecom: '企业微信',
      wechat: '微信',
      qqbot: 'QQBot',
      yunzhijia: '云之家',
      addChannel: '添加渠道',
      channelsTitle: 'IM 渠道',
      disabled: '已停用',
      editChannel: '编辑渠道',
      deleteConfirm: '确定删除该渠道？删除后无法恢复。',
      channelName: '渠道名称',
      channelNamePlaceholder: '输入渠道名称，方便辨识',
      channelNameDefaultHint: '默认为平台名称，可自行修改；留空保存时也会使用平台名称',
      platform: '平台',
      mode: '接入模式',
      outputMode: '输出模式',
      outputStream: '流式输出',
      outputFull: '完整输出',
      callbackUrl: '回调地址',
      empty: '暂无 IM 渠道',
      unnamed: '未命名渠道',
      docLink: '查看接入文档',
      wecomConsole: '企业微信管理后台',
      feishuConsole: '飞书开放平台',
      larkConsole: 'Lark 开放平台',
      slackConsole: 'Slack API 控制台',
      telegramConsole: 'Telegram BotFather',
      dingtalkConsole: '钉钉开放平台',
      dingtalkCardTemplateId: '卡片模板 ID（可选）',
      dingtalkCardTemplateIdHint: '在 open-dev.dingtalk.com/fe/card 创建 AI 卡片模板，启用后支持打字机效果的流式输出',
      mattermostConsole: 'Mattermost 集成说明',
      qqbotConsole: 'QQ 开放平台',
      qqbotAPIBaseURLHint: '可选，留空则使用默认正式环境 API 地址。',
      qqbotGatewayURLHint: '可选，留空则自动获取通用 WebSocket 接入点。',
      yunzhijiaConsole: '云之家开放平台',
      yunzhijiaRobotDoc: '机器人消息文档',
      yunzhijiaImageDoc: '开发者平台（图片功能）',
      yunzhijiaModeHint: '支持 Webhook 和 WebSocket；WebSocket 模式无需配置公网回调地址。',
      yunzhijiaSendMsgUrl: '发送消息地址',
      yunzhijiaSendMsgUrlHint: '用于机器人回复消息。',
      yunzhijiaSecret: '签名密钥（可选）',
      yunzhijiaSecretPlaceholder: '云之家机器人设置中的 HmacSHA1 签名密钥',
      yunzhijiaSecretHint: '配置后，将对传入的回调请求进行 HmacSHA1 签名验证',
      yunzhijiaAppId: '应用 App ID（图片下载）',
      yunzhijiaAppIdPlaceholder: '云之家开放平台应用 App ID',
      yunzhijiaAppSecret: '应用 App Secret（图片下载）',
      yunzhijiaAppSecretPlaceholder: '云之家开放平台应用 Secret',
      yunzhijiaAppCredentialHint: '用于获取 appAccessToken 并下载用户发送的图片文件。',
      yunzhijiaTimeout: 'HTTP 超时时间（秒）',
      yunzhijiaTimeoutHint: '通过发送消息地址回复的超时时间，默认 10 秒',
      yunzhijiaAllowedHostSuffix: '允许的主机后缀',
      yunzhijiaAllowedHostSuffixHint: '限制发送消息地址的目标域名后缀，提升安全性（如 yunzhijia.com）',
      yunzhijiaSendMsgUrlRequired: '请填写云之家机器人设置中的发送消息地址',
      mattermostModeHint: 'Mattermost 仅支持 Webhook（出站 Webhook + Bot Token）。',
      mattermostPostToMain: '回复显示在频道主时间线',
      mattermostPostToMainHint: '开启后 Bot 回复作为频道内新帖子；关闭（默认）则作为原消息的线程回复，主窗口仅显示「N 条回复」。',
      modeHint: '推荐使用 WebSocket 方式接入，配置更简单',
      consoleTip: '前往获取凭证信息',
      wecomWSEndpointHint: '可选，私有化部署时填写自定义 WebSocket 地址，留空则使用默认公有云地址。内网地址需将域名加入 SSRF_WHITELIST 环境变量',
      wecomAPIBaseURLHint: '可选，私有化部署时填写自定义 API 地址，留空则使用默认公有云地址。内网地址需将域名加入 SSRF_WHITELIST 环境变量',
      feishuAPIBaseURLHint: '可选。若服务器能直连外网则留空；若需通过代理才能访问飞书，填写反向代理地址（如 nginx，http://host:port）。内网地址需将域名加入 SSRF_WHITELIST 环境变量',
      fileKnowledgeBase: '文件保存知识库',
      fileKnowledgeBasePlaceholder: '选择知识库（可选）',
      fileKnowledgeBaseHint: '配置后，用户发送的文件将自动保存到该知识库中',
      sessionMode: '会话模式',
      sessionModeUser: '按用户（默认）',
      sessionModeThread: '按话题',
      sessionModeHint: '用户模式：每个用户独立对话，使用 /clear 开始新对话。话题模式：每个消息话题独立对话，同一话题中多人可协作。',
      replyLanguage: '回复语言',
      replyLanguageDefault: '跟随系统默认语言',
      replyLanguageHint: '固定该渠道的智能体回复语言；留空时使用部署的默认语言。',
      wechatScanBind: '扫码绑定微信',
      wechatScanning: '请使用微信扫描二维码',
      wechatBindSuccess: '微信绑定成功',
      wechatRebind: '重新绑定',
      wechatHint: '需要 iOS 微信 8.0.70+ 版本，仅支持单聊消息',
      wechatQRExpired: '二维码已过期，请重新获取',
      wechatBinding: '绑定中...',
      sectionChannel: '渠道信息',
      sectionConnection: '连接设置',
      sectionCredentials: '平台凭证',
      selectPlatform: '选择平台',
      selectPlatformDesc: '选择要接入的即时通讯平台',
      enabled: '启用渠道',
      stepBasic: '基本信息',
      stepConnection: '连接设置',
      stepKnowledge: '文件存储',
      stepCredentials: '平台凭证',
      sectionAccess: '接入与输出',
      sectionSession: '会话设置',
      sectionCallback: '回调地址',
      sectionKnowledge: '文件存储',
      sectionStatus: '运行状态'
    },
    embed: {
      title: '网页嵌入'
    },
    tools: {
      thinking: '思考',
      thinkingDesc: '动态和反思性的问题解决思考工具',
      todoWrite: '制定计划',
      todoWriteDesc: '创建结构化的研究计划',
      askUser: '向用户提问',
      askUserDesc: '在缺少关键信息时向用户提问，并等待回答后继续',
      searchKnowledge: '检索知识库',
      searchKnowledgeDesc: '语义、关键词或混合检索知识库分块',
      readDocument: '阅读文档',
      readDocumentDesc: '读取文档元数据与分块内容，支持分页和文内查找',
      listDocuments: '浏览文档列表',
      listDocumentsDesc: '分页列出知识库中的文档',
      queryGraph: '查询知识图谱',
      queryGraphDesc: '从知识图谱中查询关系',
      dbQuery: '查询数据库',
      dbQueryDesc: '查询数据库中的信息',
      dataAnalysis: '数据分析',
      dataAnalysisDesc: '理解数据文件并进行数据分析',
      dataSchema: '查看数据元信息',
      dataSchemaDesc: '获取表格文件的元信息',
      requiresKb: '（需要配置知识库）',
      requiresRagKb: '（需要关联启用向量/关键词索引的知识库）',
      requiresWikiKb: '（需要关联启用 Wiki 能力的知识库）',
      wikiSearch: '搜索 Wiki',
      wikiSearchDesc: '在 Wiki 知识库中按关键词/语义搜索页面',
      wikiReadPage: '阅读 Wiki 页面',
      wikiReadPageDesc: '读取指定 Wiki 页面的完整内容',
      wikiFlagIssue: '标记 Wiki 问题',
      wikiFlagIssueDesc: '标记页面中存在的事实错误或合并冲突问题',
      wikiWritePage: '创建/覆盖 Wiki',
      wikiWritePageDesc: '创建新页面或完全覆盖已有 Wiki 页面',
      wikiReplaceText: '局部替换 Wiki',
      wikiReplaceTextDesc: '替换 Wiki 页面中的特定文本',
      wikiRenamePage: '重命名 Wiki',
      wikiRenamePageDesc: '重命名 Wiki 页面并自动更新关联链接',
      wikiDeletePage: '删除 Wiki',
      wikiDeletePageDesc: '删除 Wiki 页面并自动清理关联死链',
      wikiReadIssue: '查看 Wiki 问题',
      wikiReadIssueDesc: '查看特定 Wiki 页面的巡检问题详情',
      wikiUpdateIssue: '更新 Wiki 问题',
      wikiUpdateIssueDesc: '更新 Wiki 页面问题的处理状态',
      webSearch: '网络搜索',
      webFetch: '网页抓取',
      groupBase: '基础',
      groupRag: '知识库检索（RAG）',
      groupWikiRead: 'Wiki 读取',
      groupWikiEdit: 'Wiki 编辑',
      groupWikiIssue: 'Wiki 巡检',
      groupData: '数据分析',
      writeWarning: '会修改 Wiki 内容',
      dangerTag: '可写',
      statusNoKb: '当前未关联任何知识库',
      kbMetricRag: 'RAG 知识库',
      kbMetricWiki: 'Wiki 知识库',
      statusInactive: '有 {count} 个已勾选工具在当前配置下无法生效',
      searchConversations: '回顾历史对话',
      searchConversationsDesc: '在用户自己的历史会话中查找之前聊过的内容',
      groupStored: '已保存但未提供的工具',
      switchManagedDesc: '由智能体的其他设置控制，而不是由此列表决定，在此勾选不会启用它。取消勾选即可移除。',
      unrecognizedDesc: '当前版本不提供该工具，智能体无法调用它。取消勾选即可移除。',
      keptUnknownWarning: '已保存。以下已保存的工具在当前版本中不提供，已保留，但智能体无法调用：{names}',
      droppedWarning: '已保存。以下工具由智能体的其他设置控制，已从工具列表中移除：{names}',
      effectiveLabel: '最终启用的工具',
      effectiveDesc: '根据当前配置计算，这是智能体保存后实际能调用的工具集合',
      effectiveEmpty: '当前没有可用工具，智能体将退化为纯模型问答'
    },
    desc: {
      name: '为智能体设置一个易于识别的名称',
      description: '简要描述智能体的用途和特点',
      systemPrompt: '自定义系统提示词，定义智能体的行为和角色',
      promptInheritance: '保持模板原文时将跟随模板更新；修改后按自定义内容保存。智能推理模式下，这里定义角色和工作要求，工具权限与本轮来源选择由系统单独控制。',
      useCustomSystemPrompt: '替换默认人设',
      useCustomSystemPromptDesc: '开启后此提示词替换平台默认人设段；工具使用与引用契约仍由平台注入。关闭时作为附加指令追加在默认人设之后。',
      leaveEmptyDefault: '（留空则使用系统默认）',
      contextTemplate: '定义如何将检索到的内容格式化后传递给模型',
      model: '选择智能体使用的大语言模型',
      temperature: '控制输出的随机性，0 最确定，1 最随机',
      maxTokens: '模型生成回复的最大 Token 数。选「默认」时为 2048；选「自定义」后按你填的数保存。',
      maxTokensAgent: '每一轮推理的最大生成 Token（含工具调用 JSON）。默认 24576。选「自定义」后按你填的数保存。',
      thinking: '启用模型的扩展思考能力（需要模型支持）',
      queryUnderstandModel: '用于问题理解（改写与意图识别）的模型，留空则复用主对话模型',
      rewriteSystemPrompt: '用于问题改写的系统提示词（留空使用默认）',
      rewriteUserPrompt: '用于问题改写的用户提示词模板（留空使用默认）',
      selectTools: '选择 Agent 可以使用的工具',
      maxIterations: '限制主 Agent 单轮模型调用次数。',
      kbScope: '选择智能体可访问的知识库范围',
      fallbackStrategy: '当无法从知识库找到相关内容时的处理方式',
      fallbackResponse: '当无法回答时返回的固定文本',
      fallbackPrompt: '当无法从知识库找到答案时，引导模型生成回复的提示词',
      memoryEnabled: '允许该智能体读取并补充你的长期记忆。关闭后，与它的对话既不会读取记忆，也不会新增记忆。空间或个人设置关闭时，这里开启也不会生效'
    },
    selection: {
      all: '全部',
      selected: '指定',
      disabled: '禁用'
    },
    promptNav: {
      ariaLabel: '提示词目录',
      system: '系统提示词',
      context: '上下文模板',
      intent: '意图提示词',
      rewriteSystem: '改写 · 系统',
      rewriteUser: '改写 · 用户',
      fallback: '检索兜底'
    },
    intentPrompts: {
      title: '意图提示词',
      sectionDesc: '为不同查询意图配置专属系统提示词；未自定义时使用系统默认模板',
      intentLabel: '意图',
      promptPlaceholder: '输入自定义系统提示词...',
      customized: '已自定义',
      empty: '暂无可用的意图模板'
    },
    placeholders: {
      available: '可用变量：',
      clickToInsert: '（点击插入）',
      hint: '（点击插入，或输入 {\'{{\'} 唤起列表）'
    },
    questionSuggestions: {
      title: '对话问题推荐'
    },
    navGroups: {
      basic: '基础',
      knowledge: '知识检索',
      capability: '能力扩展'
    }
  },
  agentStream: {
    saveToKb: {
      emptyContent: '当前回答为空，无法保存到知识库',
      editorOpened: '已打开编辑器，请选择知识库后保存'
    },
    copy: {
      emptyContent: '当前回答为空，无法复制',
      success: '已复制到剪贴板',
      failed: '复制失败，请手动复制'
    },
    toolStatus: {
      calling: '正在调用 {name}...',
      searchKb: '检索知识库',
      searchKbFailed: '检索知识库失败',
      searchMixed: '检索知识库和网络',
      searchMixedFailed: '检索失败',
      webSearch: '网络搜索',
      webSearchFailed: '网络搜索失败',
      grepSearch: '搜索关键词',
      grepSearchFailed: '搜索关键词失败',
      getDocInfo: '获取文档信息',
      getDocInfoFailed: '获取文档信息失败',
      viewDocument: '查看文档',
      thinkingDone: '完成思考',
      thinkingFailed: '思考失败',
      updateTodos: '更新任务列表',
      updateTodosFailed: '更新任务列表失败',
      imageAnalyzing: '正在查看图片内容...',
      imageAnalysisDone: '已查看图片内容',
      imageAnalysisFailed: '图片内容查看失败',
      attachmentParsing: '正在解析附件...',
      attachmentParsingDone: '已解析附件',
      attachmentParsingFailed: '附件解析失败',
      queryUnderstanding: '正在理解问题...',
      queryUnderstandDone: '已完成问题理解',
      called: '调用 {name}',
      calledFailed: '调用 {name} 失败',
      shellExecRunning: '正在执行沙箱命令...'
    },
    mcp: {
      discoverTools: '发现 MCP 工具',
      listServers: '查看 MCP 服务',
      listTools: '查看 MCP 工具',
      searchTools: '搜索 MCP 工具',
      describeTool: '读取工具定义',
      callTool: '调用 MCP 工具',
      showing: '已显示 {count} / {total} 项',
      moreAvailable: '还有更多结果',
      empty: '没有可显示的项',
      parameters: '参数',
      expand: '展开说明',
      collapse: '收起',
      required: '必填',
      fullSchema: '完整参数定义',
      failed: 'MCP 操作失败',
      result: '执行结果'
    },
    ragPipeline: {
      searching: '正在检索知识库...',
      searchingWithQuery: '正在检索知识库：「{query}」',
      searchingWeb: '正在检索网络...',
      searchingWebWithQuery: '正在检索网络：「{query}」',
      searchingMixed: '正在检索知识库和网络...',
      searchingMixedWithQuery: '正在检索知识库和网络：「{query}」',
      searchDone: '检索完成'
    },
    attachmentParsing: {
      parsedSummary: '已解析 {count} 个附件',
      parsedWithSkipped: '已解析 {parsed} 个附件，{skipped} 个未完成已跳过',
      noneReady: '没有可用的已解析附件'
    },
    knowledgeChunksList: {
      chunkRange: '已加载 {fetched} / {total} 个分块',
      page: '第 {page} 页，每页 {pageSize} 个',
      offsetRange: '第 {from}–{to} 块',
      queryMatches: '文档内搜索「{query}」命中 {count} 处',
      queryNoMatch: '文档内搜索「{query}」无匹配'
    },
    grepResults: {
      chunkHits: '{count} 片段',
      keywordHits: '{count} 次',
      titleMatch: '标题匹配',
      faqEntry: 'FAQ 条目'
    },
    search: {
      noResults: '未找到匹配的内容',
      candidatesBelowThreshold: '命中 {count} 条候选，相关性不足，未用于回答',
      foundResultsFromFiles: '找到 {count} 个结果，来自 {files} 个文件',
      foundResults: '找到 {count} 个结果',
      foundMixedResults: '找到 {count} 个结果（{docCount} 篇文档，{webCount} 条网页）',
      webResults: '找到 {count} 条网页',
      grepSummary: '找到 {chunks} 个匹配片段，来自 {docs} 个文档'
    },
    plan: {
      inProgress: '进行中',
      pending: '待处理',
      completed: '已完成'
    },
    toolSummary: {
      getDocument: '获取文档：{title}',
      document: '文档',
      listChunks: '查看 {title}',
      listFaqEntry: '查看 FAQ：{question}',
      deepThinking: '深度思考'
    },
    entityLink: {
      kb: '知识库',
      doc: '文档',
      chunk: '片段'
    },
    citation: {
      notFound: '未找到内容',
      loadFailed: '加载失败',
      noKbForWiki: '无法识别关联的知识库，无法打开 Wiki'
    },
    weknoraDocs: {
      pages: '{count} 篇文档',
      hits: '匹配 {count} 个章节',
      empty: '没有匹配的文档',
      outline: '目录',
      content: '正文',
      truncated: '正文未读完，可以继续读取',
      failed: '读取失败',
      openDoc: '在文档站打开'
    },
    operations: {
      found: '{count} 个可执行操作',
      unavailableCount: '{count} 个当前不可用',
      empty: '没有匹配的操作',
      unavailableHeading: '当前不可用',
      parameters: '参数',
      required: '必填',
      enum: '可选值',
      range: '范围 {min}–{max}',
      truncated: '结果已截断',
      emptyResult: '没有返回数据',
      failed: '操作失败',
      meta: '附加信息',
      risk: {
        read: '只读',
        probe: '检测',
        write: '写入',
        destructive: '不可恢复'
      },
      names: {
        session: {
          list: '获取会话列表'
        },
        automation: {
          list: '获取自动化列表',
          create: '创建自动化',
          validate_trigger: '校验运行时间',
          get: '获取自动化详情',
          update: '更新自动化',
          delete: '删除自动化',
          pause: '暂停自动化',
          resume: '恢复自动化',
          run_now: '立即运行自动化',
          list_runs: '获取自动化运行记录'
        },
        skill: {
          list_installed: '获取已安装技能列表',
          install: '安装技能',
          get_installed: '获取已安装技能详情',
          uninstall: '卸载技能',
          set_enabled: '设置技能启用状态',
          list: '获取可执行技能列表',
          list_catalog: '获取工作空间技能列表',
          get_catalog: '获取工作空间技能详情',
          install_catalog: '将目录技能安装到沙箱'
        },
        model: {
          list: '获取模型列表',
          list_providers: '获取模型厂商列表',
          get_provider: '获取模型厂商详情',
          get: '获取模型详情',
          delete: '删除模型',
          update: '更新模型显示信息',
          copy: '复制模型配置'
        },
        message: {
          chat_history_stats: '获取聊天历史统计',
          search: '搜索历史对话',
          list: '获取消息历史'
        },
        mcp_service: {
          list: '获取 MCP 服务列表',
          create: '创建 MCP 服务',
          get: '获取 MCP 服务详情',
          update: '更新 MCP 服务',
          delete: '删除 MCP 服务',
          test: '测试 MCP 服务连接',
          list_tools: '实时查询 MCP 工具',
          get_metadata: '查看已同步 MCP 工具',
          refresh_metadata: '同步 MCP 工具目录'
        },
        web_search_provider: {
          list: '获取网络搜索服务列表',
          get: '获取网络搜索服务详情',
          list_types: '获取网络搜索服务类型',
          test: '测试网络搜索连接',
          update: '修改网络搜索服务',
          delete: '删除网络搜索服务'
        },
        system: {
          get_info: '查询版本与系统信息'
        },
        workspace: {
          get: '查询当前空间信息',
          update: '修改当前空间基本信息',
          list_members: '查询当前空间成员'
        },
        system_admin: {
          list_admins: '查询系统管理员',
          list_users: '查询平台用户',
          list_settings: '查询系统设置',
          get_queues: '查询任务队列运行状态',
          list_tasks: '查询队列任务'
        },
        wiki: {
          list_folders: '获取 Wiki 文件夹列表',
          create_folder: '创建 Wiki 文件夹',
          list_issues: '获取 Wiki 页面问题列表',
          lint: '检查 Wiki 页面',
          move_page: '移动 Wiki 页面',
          get_page: '获取 Wiki 页面',
          rebuild_links: '重建 Wiki 链接',
          revert: '还原 Wiki 页面版本',
          list_revisions: '获取 Wiki 页面版本列表',
          get_stats: '获取 Wiki 统计信息'
        },
        knowledge: {
          list: '获取知识列表',
          list_folders: '获取知识文件夹列表',
          rename_folder: '重命名或移动文件夹',
          create_manual: '手动创建知识',
          create_from_url: '从链接创建知识',
          batch_delete: '批量删除知识',
          batch_reparse: '批量重新解析知识',
          move_to_folder: '移动知识到文件夹',
          update_manual: '更新手动创建的知识',
          move: '移动知识到其他知识库',
          get_move_progress: '获取知识移动进度',
          set_tags: '设置知识标签',
          get: '获取知识详情',
          update: '更新知识',
          delete: '删除知识',
          cancel_parse: '取消知识解析',
          reparse: '重新解析知识',
          get_parse_progress: '获取知识解析进度'
        },
        faq: {
          batch_update: '批量修改 FAQ 状态和标签',
          list_entries: '获取 FAQ 条目列表',
          delete_entries: '批量删除 FAQ 条目',
          get_entry: '获取 FAQ 条目详情',
          update_entry: '更新 FAQ 条目',
          add_similar_questions: '添加相似问',
          create_entry: '创建 FAQ 条目'
        },
        knowledge_base: {
          list_parser_engines: '获取可用解析引擎',
          copy: '复制知识库内容',
          duplicate: '复制知识库设置',
          get_copy_progress: '获取知识库复制进度',
          list: '获取知识库列表',
          create: '创建知识库',
          get: '获取知识库详情',
          delete: '删除知识库',
          update: '更新知识库',
          list_activity: '获取知识库活动记录',
          search: '搜索知识库',
          list_move_targets: '获取可移动的目标知识库',
          generate_profile: '生成知识库描述',
          list_tags: '获取知识库标签列表',
          create_tag: '创建知识库标签',
          update_tag: '更新知识库标签',
          delete_tag: '删除知识库标签',
          list_shared: '获取共享知识库列表'
        },
        chunk: {
          get: '获取分块详情',
          update: '更新分块',
          list_revisions: '获取分块历史版本',
          revert: '恢复分块历史版本',
          list: '获取知识分块列表'
        },
        artifact: {
          list: '获取产物库文件列表'
        },
        agent: {
          list: '获取智能体列表',
          create: '创建智能体',
          get: '获取智能体详情',
          delete: '删除智能体',
          update: '更新智能体',
          copy: '复制智能体'
        },
        data_source: {
          list: '获取数据源列表',
          get: '获取数据源详情',
          test: '测试数据源连接',
          sync: '同步数据源',
          pause: '暂停数据源同步',
          resume: '恢复数据源同步',
          list_sync_logs: '获取数据源同步记录',
          get_sync_log: '获取数据源同步进度',
          list_resources: '查询数据源可同步资源',
          update_sync: '修改数据源同步配置'
        }
      }
    },
    shellExec: {
      workDir: '目录',
      exitCode: '退出码',
      stdout: '标准输出',
      stderr: '标准错误',
      emptyOutput: '无输出',
      truncated: '输出已截断',
      killed: '已超时终止',
      binarySuppressed: '二进制输出已省略，请将文件写入产物目录后下载'
    },
    sandboxFiles: {
      found: '找到 {count} 个文件',
      empty: '暂无文件',
      truncated: '列表已截断',
      wrote: '已写入',
      replacements: '替换 {count} 处',
      moreLines: '另有 {count} 行'
    },
    imageView: {
      summary: '已查看「{file}」第 {numbers} 张图片，共 {total} 张',
      single: '已查看图片「{file}」',
      descriptionsHeading: '视觉模型的图片描述',
      imageLabel: '图片 #{n}',
      noDescription: '未能生成描述',
      remaining: '还有 {count} 张未查看'
    },
    attachmentTarget: {
      list: '全部附件',
      file: '附件',
      images: '{name} 中的图片',
      imagesUnnamed: '附件中的图片',
      image: '{name} 第 {n} 张图片',
      imageUnnamed: '附件第 {n} 张图片'
    },
    skillFiles: {
      heading: '技能文件',
      script: '脚本',
      instructions: '技能说明'
    },
    openPage: {
      open: '打开',
      retired: '已停用',
      openForm: '打开并填写',
      opened: '助手已打开',
      back: '返回',
      endpoint: '将连接到：',
      draftHint: '已按助手的建议预填。请补全密钥等凭据，检查后自己保存。'
    },
    pageEdit: {
      title: '已填写 {count} 处',
      undo: '撤销',
      undone: '已撤销这次填写',
      undoSkipped: '{count} 处已被你改过或不在页面上，未撤销',
      unsaved: '尚未保存，请检查后在页面上自行保存'
    },
    pageAccess: {
      viewed: '已查看当前页面：{location}'
    },
    collaboration: {
      tabs: '任务标签页',
      updates: '{count} 条进展',
      mainConversation: '主对话',
      assignment: '任务说明',
      title: '子任务',
      unnamed: '未命名任务',
      phase: {
        tool_running: '正在使用工具',
        tool_succeeded: '工具已完成',
        tool_failed: '工具失败'
      },
      status: {
        queued: '排队中',
        running: '进行中',
        waiting: '等待你处理',
        succeeded: '已完成',
        failed: '失败',
        interrupted: '已中断',
        cancelled: '已取消',
        needs_attention: '需要处理',
        cancelling: '正在取消',
        unknown: '状态未知'
      }
    },
    tools: {
      searchKnowledge: '知识库检索',
      grepChunks: '搜索关键词',
      webSearch: '网络搜索',
      webFetch: '网页抓取',
      getDocumentInfo: '获取文档信息',
      listKnowledgeChunks: '查看知识分块',
      getRelatedDocuments: '查找相关文档',
      getDocumentContent: '获取文档内容',
      wikiReadSourceDoc: '精读源文档',
      readDocument: '阅读文档',
      listDocuments: '浏览文档列表',
      todoWrite: '计划管理',
      askUser: '向用户提问',
      requestSecureForm: '请求登录凭据',
      browserFillSecret: '填写登录凭据',
      knowledgeGraphExtract: '知识图谱抽取',
      thinking: '思考',
      attachmentParsing: '解析附件',
      imageAnalysis: '查看图片内容',
      queryUnderstand: '理解问题',
      queryKnowledgeGraph: '知识图谱查询',
      readSkill: '读取技能',
      executeSkillScript: '执行技能脚本',
      listSandboxFiles: '列出沙箱文件',
      readFile: '读取文件',
      readSandboxFile: '读取沙箱文件',
      writeSandboxFile: '写入沙箱文件',
      editSandboxFile: '编辑沙箱文件',
      shellExec: '执行沙箱命令',
      dataAnalysis: '数据分析',
      dataSchema: '数据结构',
      databaseQuery: '数据库查询',
      findOperations: '查找操作',
      runOperation: '执行操作',
      spawn_agent: '启动智能体',
      list_agents: '查看智能体',
      send_message: '发送消息',
      followup_task: '继续任务',
      interrupt_agent: '中断智能体',
      wait_agent: '等待智能体',
      openPage: '打开页面',
      viewPage: '查看页面',
      searchWeKnoraDocs: '搜索产品文档',
      readWeKnoraDoc: '阅读产品文档',
      readPage: '查看当前页面',
      selectTab: '切换标签',
      fillPage: '填写页面'
    },
    mcpOAuth: {
      waiting: '等待授权 · {target}',
      waitingStatus: '等待授权',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '需要授权 {target} 才能继续',
      titleWithService: 'OAuth 授权 · {service}',
      titleWithTool: 'OAuth 授权 · {service} › {tool}',
      desc: '点击授权将打开新窗口完成登录，授权成功后会自动继续本次工具调用。',
      authorize: '去授权',
      skip: '跳过',
      countdownShort: '{seconds}s',
      authorizedTag: '已授权',
      timedOutTag: '授权超时',
      canceledTag: '已取消',
      authorizedToast: '授权成功，正在继续',
      startFailed: '发起授权失败',
      resumeFailed: '恢复执行失败，请重试',
      skipFailed: '跳过失败，请重试'
    },
    hostReview: {
      denied: '自动审批已拒绝：{reason}'
    },
    hostApproval: {
      command: '命令',
      grantPath: '需要访问',
      accessWrite: '读写',
      accessRead: '只读',
      firstAttemptRan: '这条命令已经执行过一次并失败，批准后会整条重新执行',
      snippet: '拦截详情',
      sessionRules: '本会话允许后，同目录下这类删除不再询问（文件名可以不同）',
      reject: '拒绝',
      approveOnce: '允许一次',
      approveSession: '本会话允许',
      approvedOnce: '已允许一次',
      approvedSession: '本会话已允许',
      rejectedTag: '已拒绝',
      submitted: '已提交',
      submitFailed: '提交失败',
      userRejected: '用户拒绝',
      fileOnly: '只授权这一个文件',
      writeMode: '方式',
      writeModeOverwrite: '覆盖',
      writeModeAppend: '追加',
      writeModeEdit: '编辑',
      writeBytes: '{bytes} 字节',
      preview: '内容',
      previewTruncated: '只显示前 64 KB',
      env: '环境变量',
      skillName: '技能',
      stdin: '标准输入',
      script: '命令运行的脚本'
    },
    toolApproval: {
      title: '人工审核',
      toolDescription: '工具说明',
      delegatedTask: '子任务',
      waitingStatus: '等待审核',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '允许调用 {target}？',
      operationQuestion: '允许{action}「{target}」？',
      operationQuestionNoTarget: '允许{action}？',
      operationTarget: '{action}「{target}」',
      characterCount: '{count} 字',
      argsLabel: '调用参数',
      argsModified: '已修改',
      allowInSession: '本会话内同类操作都允许',
      countdownShort: '{seconds}s',
      approve: '通过并执行',
      reject: '拒绝',
      approvedTag: '已通过',
      rejectedTag: '已拒绝',
      parked: '已转入后台等待，可稍后处理',
      parkedUntil: '已转入后台等待，{time} 前可处理',
      abandonedTag: '已放弃',
      canceledTag: '已取消',
      invalidJson: '参数不是合法 JSON',
      submitted: '已提交',
      submitFailed: '提交失败',
      userRejected: '用户拒绝',
      value: {
        document: '文档',
        faq: '问答',
        wiki: 'Wiki',
        on: '开',
        off: '关',
        vector: '向量',
        keyword: '关键词',
        graph: '图谱',
        quickAnswer: '快速问答',
        smartReasoning: '智能推理',
        indexSep: '、'
      },
      detail: {
        type: '类型',
        embeddingModel: '嵌入模型',
        summaryModel: '摘要模型',
        captionModel: '图片描述',
        speechModel: '语音识别',
        storage: '存储',
        indexes: '索引',
        name: '名称',
        title: '标题',
        status: '状态',
        summary: '简介',
        model: '模型',
        mode: '模式',
        url: '链接',
        from: '从',
        to: '到',
        folder: '目录',
        page: '页面',
        version: '版本',
        documents: '文档',
        knowledgeBases: '知识库',
        mcpServices: 'MCP 服务',
        skills: '技能',
        webSearch: '联网搜索',
        multiTurn: '多轮对话',
        transport: '传输方式',
        authentication: '认证方式',
        usageInstructions: '使用说明',
        displayName: '显示名称',
        enabled: '启用',
        sandbox: '沙箱',
        sandboxes: '沙箱',
        systemPrompt: '系统提示词',
        content: '内容',
        kbScope: '知识库范围',
        mcpScope: 'MCP 范围',
        skillsScope: '技能范围'
      },
      grantLapsed: {
        changed: '之前的允许已失效：自动化的 Agent 配置、成员角色或权限上限已变化。',
        expired: '之前的允许已过期。',
        idle: '之前的允许因长期未使用已失效。'
      }
    },
    promptDock: {
      approvalTitle: '需要你审核',
      oauthTitle: '需要你授权',
      secureFormTitle: '需要你填写凭据',
      waiting: '等待你处理',
      handle: '去处理',
      pager: '{current} / {total}',
      previous: '上一个',
      next: '下一个',
      collapse: '收起',
      expand: '展开'
    },
    secureForm: {
      onlyFillInto: '只会填入：{domains}',
      observedAt: '浏览器当前页面：{origin}',
      originUnknown: '无法确认浏览器当前页面，请确认浏览器停在要登录的网站上再填写',
      originMismatch: '浏览器当前页面（{origin}）与要登录的网站不一致，请确认后再填写',
      originInsecure: '浏览器当前页面不是 HTTPS，凭据不会填入',
      savedAccount: '已保存的账号',
      useNew: '使用新的账号密码',
      username: '账号',
      password: '密码',
      saveToVault: '保存到保险库',
      useOnce: '仅用一次',
      fill: '填写',
      decline: '拒绝',
      submittedHidden: '已提交（内容不显示）',
      declined: '已拒绝',
      timedOut: '超时未填写',
      canceled: '已取消',
      submitFailed: '提交失败',
      savedButClosed: '凭据已保存到保险库，但这次请求已结束'
    },
    askUser: {
      answerLabel: '你的回答',
      title: '向你提问',
      selectPlaceholder: '请选择',
      textPlaceholder: '输入你的回答',
      otherPlaceholder: '其他（可选）',
      decline: '不回答',
      submit: '提交',
      declinedTag: '已拒绝回答',
      submitted: '已提交',
      answeredTag: '已回答',
      timedOutTag: '超时未回答',
      canceledTag: '已取消',
      unansweredTag: '未回答',
      submitFailed: '提交失败'
    }
  },
  kbSettings: {
    parser: {
      title: '解析引擎',
      description: '为不同文件类型选择文档解析引擎。未配置的文件类型将使用内置解析引擎。',
      loading: '加载中...',
      noEngineAvailable: '暂无可用解析引擎，或文档解析服务未配置。',
      default: '默认',
      goConfig: '前往配置 →',
      noEngine: '无可用引擎',
      fileTypePdf: 'PDF 文档',
      fileTypeWord: 'Word 文档',
      fileTypePpt: '演示文稿',
      fileTypeExcel: 'Excel 表格',
      xlsxFirstRowAsHeader: '将首行作为列标题，并保留在每行上下文中',
      fileTypeEbook: '电子书',
      fileTypeWebArchive: '网页归档',
      fileTypeCsv: 'CSV 文件',
      fileTypeText: '纯文本',
      fileTypeJson: 'JSON 文件',
      fileTypeImage: '图片',
      fileTypeAudiovisual: '音频',
      engines: {
        opendataloader: {
          name: 'OpenDataLoader',
          desc: 'OpenDataLoader PDF 解析引擎（版面分析，需 Java 11+ 与 opendataloader-pdf）'
        },
        markitdown: {
          name: 'MarkItDown',
          desc: 'Microsoft MarkItDown 文档转换工具（支持 PDF/Office/HTML 等）'
        },
        paddleocr_vl_cloud: {
          name: 'PaddleOCR-VL Cloud',
          desc: 'PaddleOCR-VL 云 API'
        },
        paddleocr_vl: {
          name: 'PaddleOCR-VL',
          desc: 'PaddleOCR-VL 自部署服务'
        },
        mineru_cloud: {
          name: 'MinerU Cloud',
          desc: 'MinerU Cloud API'
        },
        mineru: {
          name: 'MinerU',
          desc: 'MinerU 自部署服务'
        },
        anydoc: {
          name: 'anydoc',
          desc: '进程内 Office 文档解析（无需外部服务）'
        },
        simple: {
          name: 'Simple',
          desc: '简单格式 & 图片解析（无需外部服务）'
        },
        builtin: {
          name: '内置',
          desc: 'DocReader 内置解析引擎（docx/pdf/xlsx 等复杂格式）'
        }
      }
    },
    storage: {
      title: '存储引擎',
      selectDescription: '选择此知识库绑定的具体存储实例。',
      defaultTag: '默认',
      instanceLabel: '存储实例',
      instanceDesc: '同一种存储类型可以配置多个不同 Endpoint、Bucket 或凭据的实例。',
      migrateHint: '知识库中已有文件，需通过存储迁移流程才能更换实例。',
      manageInstances: '管理存储实例',
      localStorage: '本地存储',
      loading: '加载中...'
    },
    vectorStore: {
      title: '向量存储',
      description: '选择此知识库要写入的向量存储。绑定不可更改 — 如需将现有 KB 迁移到其他存储，请创建新 KB 并重新索引。',
      loading: '正在加载向量存储列表...',
      engineLabel: '向量存储',
      engineDesc: '从全局向量存储配置中选择，或保持系统默认以使用空间的 RETRIEVE_DRIVER 引擎。',
      boundLabel: '已绑定的向量存储',
      systemDefault: '系统默认',
      immutableHint: '创建后不可更改。如需迁移，请创建一个绑定到目标存储的新 KB 并重新索引。',
      immutableEdit: '向量存储绑定在创建后无法更改。',
      unavailableHint: '绑定的向量存储当前不可用，请在设置 → 向量存储中检查其连接配置。',
      goGlobalSettings: '前往向量存储设置'
    }
  },
  vectorStoreBadge: {
    systemDefault: '系统默认',
    sharedFromOrg: '来自其他组织的共享',
    unknownStore: '未知存储',
    unavailable: '不可用'
  },
  tools: {
    multiKbSearch: '跨库搜索',
    searchKnowledge: '检索知识库',
    readDocument: '阅读文档',
    listDocuments: '浏览文档列表',
    knowledgeSearch: '知识库搜索',
    grepChunks: '搜索关键词',
    getChunkDetail: '获取片段详情',
    listKnowledgeChunks: '查看知识分块',
    listKnowledgeBases: '列出知识库',
    getDocumentInfo: '获取文档信息',
    queryKnowledgeGraph: '查询知识图谱',
    think: '深度思考',
    todoWrite: '制定计划'
  },
  commandPalette: {
    placeholder: '搜索知识库、文件、对话…',
    clearRecent: '清除',
    retrieval: '检索参数',
    untitledSession: '未命名对话',
    hotkey: {
      select: '选择',
      enter: '打开',
      cmdNumber: '直接打开',
      cmdEnter: '发起对话',
      esc: '关闭'
    },
    empty: {
      noResults: '没有找到匹配结果',
      askAi: '直接向 AI 提问',
      adjustRetrieval: '调整检索参数'
    },
    quick: {
      newChat: '新建对话',
      knowledgeBases: '打开知识库',
      agents: '打开智能体',
      organizations: '打开共享空间',
      settings: '打开设置',
      productTour: '新手引导',
      assistant: '打开 {name}'
    },
    match: {
      vector: '向量',
      keyword: '关键字'
    },
    group: {
      chunks: '知识库文件',
      messages: '对话消息',
      kbs: '知识库',
      agents: '智能体',
      sessionsByTitle: '对话（按标题）',
      commands: '命令',
      recent: '最近搜索',
      quickActions: '快捷操作'
    },
    scope: {
      placeholder: '在本知识库中搜索…',
      remove: '移除范围过滤（Backspace）'
    }
  },
  assistant: {
    title: '小知助手',
    newConversation: '新对话',
    history: '历史对话',
    untitledConversation: '未命名对话',
    historyEmpty: '暂无历史对话',
    historyFailed: '加载历史对话失败',
    loadMore: '加载更多',
    resize: '调整助手宽度',
    welcomeTitle: '有什么可以帮你？',
    agentWelcomeDesc: '可以检查这个智能体的配置、调整模型或查看它能检索的知识库。',
    welcomeDesc: '我可以解答小知的使用问题，整理知识与文档，帮你配置智能体、工具和自动化。',
    startFailed: '启动助手失败，请重试',
    chooseAction: '选择一个功能，或直接输入你的需求。',
    askAboutAnswer: '就这条回答问 {name}',
    starters: {
      agentConfig: '这个智能体的配置有哪些可以改进的地方？',
      agentModel: '这个智能体适合换成什么模型？',
      agentKnowledge: '它能检索哪些知识库？',
      wikiIssues: '这篇 Wiki 有哪些内容需要补充或核实？',
      wikiSummary: '这篇 Wiki 的核心内容是什么？',
      documentSummary: '这篇文档有哪些关键结论？',
      recentActivity: '最近上传或更新了哪些文档？',
      agents: '这些智能体分别适合回答什么问题？',
      messageSources: '这个回答的依据是什么？',
      messageCheck: '这个回答有没有说错？',
      modelCheck: '这个模型的配置适合当前用途吗？',
      modelUsage: '哪些智能体和知识库在用这些模型？',
      mcpTools: '这个 MCP 服务提供哪些工具？',
      mcpCheck: '使用这个服务还需要配置什么？',
      modelSetup: '我还需要配置哪些模型？',
      mcpSetup: '怎样接入一个 MCP 服务？',
      releaseHighlights: '当前版本主要更新了哪些内容？',
      gettingStarted: '第一次使用小知，应该先配置什么？',
      workflow: '知识库、智能体和自动化该怎么配合使用？',
      knowledgeOverview: '这些知识库分别适合查哪些内容？',
      knowledgeType: '文档、FAQ 和 Wiki，我该怎么选？',
      knowledgeOrganize: '我有一批资料，怎样整理成好用的知识库？',
      knowledgeTopics: '这些文档分别讲了什么？',
      knowledgeGaps: '哪些文档解析失败或还没完成？',
      faqCoverage: '这些问答覆盖了哪些高频问题？',
      faqDuplicates: '哪些问答内容重复，可以合并？',
      faqImprove: '哪些答案需要补充或更新？',
      documentSteps: '把这篇文档里的做法整理成操作步骤',
      documentFaq: '这篇文档可以提炼出哪些常见问答？',
      wikiSources: '这篇 Wiki 的结论有哪些来源支撑？',
      agentCreate: '怎样新建一个能查知识库的智能体？',
      agentChoose: '查知识库时，该用这里的哪个智能体？',
      automationIdeas: '哪些重复工作适合交给自动化？',
      automationCreate: '帮我设一个任务，每周汇总知识库的更新',
      automationOverview: '我的自动化任务最近运行得怎么样？',
      automationSummary: '这个任务最近一次运行产出了什么？',
      automationSchedule: '这个任务下次什么时候运行？',
      automationImprove: '这个任务的提示词和执行安排还能怎么改进？',
      skillFind: '这里有哪些技能适合加到智能体上？',
      skillAdd: '怎样把新技能添加并启用到智能体？',
      skillUse: '已添加的技能分别能做什么？',
      mcpFind: '这些 MCP 服务里，智能体能调用哪些工具？',
      mcpExamples: '怎样让智能体使用这些 MCP 工具？',
      mcpUsage: '这个服务的工具怎么用？举个例子',
      modelFit: '这个模型更适合处理哪些任务？',
      modelTypes: '对话、向量和重排模型分别怎么选？',
      browserConnect: '怎样把浏览器连接给智能体使用？',
      browserTasks: '用浏览器可以自动完成哪些网页操作？',
      browserReconnect: '浏览器显示离线时，要怎么重连？',
      messageReuse: '把这个回答整理成可以照着做的步骤',
      chatSummary: '这次对话主要问了什么、得到了哪些结果？',
      chatCheck: '最后一轮回答有没有漏掉或说错的地方？',
      chatFollowup: '基于这次对话，还能接着问哪些问题？',
      artifactRecent: '最近生成了哪些文件？',
      artifactSources: '这些文件分别来自哪次对话？',
      artifactCreate: '怎样让智能体把结果保存成文件？',
      organizationShared: '这些共享空间分别共享了哪些知识库和智能体？',
      organizationJoin: '怎样加入一个已有的共享空间？',
      organizationCreate: '怎样创建一个共享空间并邀请成员？'
    },
    context: {
      currentPage: '当前页面',
      detach: '不附带当前页面',
      attachedTip: '已附带当前页面：{path}',
      detachedTip: '点击附带当前页面：{path}',
      chatMessage: '这条回答',
      pages: {
        knowledge_base: '知识库',
        wiki: 'Wiki',
        agent_editor: '智能体编辑',
        settings_models: '模型管理',
        mcp_services: 'MCP 服务',
        settings: '设置',
        chat: '对话'
      }
    },
    access: {
      title: '权限等级',
      capped: '空间管理员未开放这一等级',
      levels: {
        auto_write: {
          label: '自动执行',
          desc: '可恢复的修改直接执行，删除仍需确认'
        },
        confirm: {
          label: '修改前确认',
          desc: '每次修改或删除前都先请你确认'
        },
        read_only: {
          label: '只读',
          desc: '只查看，不做任何修改'
        }
      },
      page: {
        label: '查看和填写当前页面',
        desc: '读取左侧页面，并可代为填写表单；不会点击按钮或保存'
      }
    },
    fillNotice: {
      title: '助手已填写 {count} 处',
      undo: '撤销',
      dismiss: '关闭'
    },
    bubble: {
      label: '助手快捷操作',
      ask: '问助手',
      polish: '润色',
      rewrite: '改写',
      translate: '翻译',
      continue: '续写',
      prompts: {
        polish: '润色选中的内容：修正错别字和不通顺的地方，不改变原意，直接在原处替换。',
        rewrite: '改写选中的内容，让表达更清晰简洁，直接在原处替换。',
        translate: '翻译选中的内容：中文译成英文，其他语言译成中文，直接在原处替换。',
        continue: '接着选中的内容往下续写一段，与上下文衔接，写在选中内容之后。'
      }
    },
    selection: {
      label: '已选中',
      lines: '已选 {count} 行',
      detach: '不带上选中内容',
      tip: '发送时会带上选中的内容：{text}',
      tipField: '发送时会带上「{field}」中选中的内容：{text}'
    },
    prompts: {
      createAgent: '请根据我的需求创建智能体：{request}。先检查当前可用的模型、知识库、MCP 和技能，选择合适的资源；只询问必要的缺失信息，遵循当前权限规则，创建成功后打开编辑页。',
      createAutomation: '请创建定时任务：{request}。未另行指定时使用时区 {timezone}。把说明写成可独立执行的完整任务，先校验时间并展示后续运行时刻，遵循当前权限规则，不提高执行权限；创建后打开任务。',
      summarizeActivity: '请仅汇总这个筛选快照中 loaded_entry_ids 指定的动态：{scope}。按筛选条件查询并翻页补齐，说明涉及资料、操作人与结果。区分操作日志与正文改动，不把已加载记录当成全部动态。',
      explainMcpTools: '请读取 MCP 服务 {id} 的缓存工具目录，说明它能做什么，给出三个实用提问示例，并注明目录是否陈旧或不完整。不要刷新目录、调用工具或修改配置。',
      answerToDocument: '请读取这条回答及原问题：{source}，整理成结构清晰的文档，保留来源与不确定性。先展示草稿并让我选择目标知识库，再按当前权限规则创建文档，不覆盖现有资料。',
      answerToFaq: '请读取这条回答及原问题：{source}，整理出标准问和准确答案。先展示草稿并让我选择目标 FAQ 知识库，检查相近条目后按当前权限规则保存，不覆盖已有条目。',
      answerToAutomation: '请读取这条回答及原问题：{source}，把需要重复完成的工作整理成可独立执行的定时任务。向我确认缺失的频率、时间和时区，校验并展示后续运行时刻，再按当前权限规则创建，不提高执行权限。',
      writePrompt: '请结合当前智能体的用途和配置，帮我起草系统提示词。如果目标还不明确，先询问我。将建议填入当前编辑器，保留模板占位符，不要保存或修改已保存的智能体。',
      refinePrompt: '请优化我附带的系统提示词，使职责、回答要求和工具使用规则更清晰，保留原意及模板占位符。将修改填入当前编辑器，不要保存或修改已保存的智能体。',
      modelFailure: '请结合当前模型配置和附带的连接错误，分析失败原因并给出排查步骤。不要读取或展示密钥，也不要修改或保存配置。',
      mcpFailure: '请结合附带的工具获取或同步错误，检查 MCP 服务（ID：{id}）并分析原因，给出排查步骤。不要读取或展示密钥，也不要重连或修改配置。',
      syncFailure: '请检查数据源「{source}」（ID：{id}）的同步记录（ID：{log}），结合附带的错误样例和失败数量分析原因。先给出处理建议，不要重试同步或修改数据源。',
      writeWikiRules: '请根据当前知识库的用途，为「{field}」起草清晰的规则。如果用途还不明确，先询问我。将建议填入对应输入框，保留系统固定的引用与输出协议，不要保存或重新解析。',
      refineWikiRules: '请优化附带的「{field}」规则，让表达更明确并保留原意。将修改填入对应输入框，保留系统固定的引用与输出协议，不要保存或重新解析。',
      analyzeChunks: '请分析附带的这次分块预览，结合原文与分块摘录、当次参数和统计，说明是否存在割裂语义、过短或过长的分块，并给出参数调整建议。区分摘录可验证的问题与需要更多原文的判断，不要修改配置或重建知识库。'
    },
    actions: {
      summarizeActivity: '汇总这 {count} 条动态',
      toolExamples: '查看使用示例',
      answerToDocument: '整理为文档',
      answerToFaq: '保存为 FAQ',
      answerToAutomation: '设为定时任务',
      writePrompt: '帮我写',
      refinePrompt: '优化提示词',
      diagnose: '分析原因',
      refineRules: '优化规则',
      analyzeChunks: '分析分块效果'
    },
    create: {
      agentTitle: '用自然语言创建智能体',
      agentAction: '用助手创建',
      agentHint: '说说它为谁服务、需要完成什么，助手会帮你选择资源并创建。',
      agentPlaceholder: '例如：创建一个产品客服助手，根据产品知识库回答使用问题，回答附上来源，找不到答案时说明原因。',
      automationTitle: '用助手创建任务',
      automationHint: '描述要做什么、何时运行，助手会帮你整理成自动化任务。',
      automationPlaceholder: '例如：每周五下午 5 点汇总产品知识库本周的更新，列出新增文档和重点变化。',
      requestLabel: '任务描述',
      manual: '手动配置',
      start: '交给助手'
    },
    settingsPages: {
      memory: {
        description: '我可以区分工作区记忆和个人记忆，并说明怎样让智能体记住空间约定。',
        q1: '工作区记忆和我的个人记忆有什么不同？',
        q2: '现在启用了哪些记忆规则？',
        q3: '怎样让智能体记住这个空间的约定？'
      },
      mymemory: {
        description: '我可以帮你查看个人记忆、说明它们会用在哪些对话，以及怎样增删。',
        q1: '这里保存了哪些我的个人记忆？',
        q2: '怎样新增或删除一条记忆？',
        q3: '这些记忆会用在哪些对话里？'
      },
      'integration-claw': {
        description: '我可以说明怎样把小知接到 Claw，以及需要安装哪个技能。',
        q1: '怎样把小知接到 Claw？',
        q2: '需要安装哪个技能？',
        q3: '连上之后能在 Claw 里做什么？'
      },
      'integration-chrome': {
        description: '我可以说明浏览器扩展能做什么、怎样安装登录，以及选中内容会发到哪里。',
        q1: '浏览器扩展能做什么？',
        q2: '怎样安装并登录这个扩展？',
        q3: '扩展里选中的内容会发到哪里？'
      },
      'integration-cli': {
        description: '我可以指导你安装并登录 CLI，并列出常用的知识库和对话命令。',
        q1: '怎样安装并登录 WeKnora CLI？',
        q2: 'CLI 能做哪些知识库和对话操作？',
        q3: '最常用的几条命令是什么？'
      },
      'integration-mcpserver': {
        description: '我可以说明怎样把小知作为 MCP 服务提供出去，以及会暴露哪些工具。',
        q1: '怎样把小知作为 MCP 服务提供出去？',
        q2: '外部客户端要怎样连接？',
        q3: '这个服务会暴露哪些工具？'
      },
      'integration-api': {
        description: '我可以说明怎样用 API 发起对话、要带哪些鉴权，并给出请求示例。',
        q1: '怎样用 API 发起一次对话？',
        q2: '调用时要带哪些鉴权信息？',
        q3: '有没有现成的请求示例？'
      },
      'integration-embed': {
        description: '我可以说明怎样把对话窗口嵌到网站，以及访客能用哪些知识库。',
        q1: '怎样把对话窗口嵌到自己的网站？',
        q2: '嵌入后访客能用哪些知识库或智能体？',
        q3: '嵌入代码里要改哪些参数？'
      },
      'integration-im': {
        description: '我可以指导你把飞书、企微等 IM 接到这个空间，并排查收不到消息的原因。',
        q1: '怎样把飞书或企微接到这个空间？',
        q2: '接入后用户要怎样在 IM 里用智能体？',
        q3: '机器人收不到消息时要检查什么？'
      },
      'system-audit-log': {
        description: '我可以帮你筛选审计记录、找出高风险操作，并说明日志保留多久。',
        q1: '最近有哪些高风险操作？',
        q2: '怎样按人、按空间筛选审计记录？',
        q3: '这些日志会保留多久？'
      },
      'platform-api-keys': {
        description: '我可以区分平台 Key 和空间 Key，并说明怎样创建和作废。',
        q1: '平台 API Key 和空间 Key 有什么区别？',
        q2: '怎样创建一把只能访问某个空间的 Key？',
        q3: '密钥泄露后要怎么立刻作废？'
      },
      'runtime-queues': {
        description: '我可以帮你查看任务队列是否卡住，以及失败任务怎样重试。',
        q1: '现在哪些任务队列卡住了？',
        q2: '解析或索引失败时要怎么重试？',
        q3: '怎样查看某个队列里正在跑的任务？'
      },
      'model-catalog': {
        description: '我可以帮你浏览模型目录、说明怎样把厂商模型加到空间。',
        q1: '目录里有哪些厂商和模型可以接入？',
        q2: '怎样把目录里的模型加到当前空间？',
        q3: '某个厂商还缺什么配置才能用？'
      },
      'system-global-other': {
        description: '我可以帮你看那些没有归类的全局配置，并说明改动前该注意什么。',
        q1: '这些未归类的配置是做什么的？',
        q2: '改其中某一项会影响什么？',
        q3: '哪些项不建议在生产环境随便改？'
      },
      'system-global-security': {
        description: '我可以解释安全策略、密钥和会话相关开关，以及改动的风险。',
        q1: '这些安全开关分别保护什么？',
        q2: '怎样轮换或作废平台级密钥？',
        q3: '哪些安全改动会影响已经登录的用户？'
      },
      'system-global-runtime': {
        description: '我可以说明运行时、任务和资源相关的全局选项分别影响什么。',
        q1: '这些运行时设置会影响哪些后台任务？',
        q2: '怎样限制并发或超时？',
        q3: '改完运行时配置何时生效？'
      },
      'system-global-tenant': {
        description: '我可以说明平台上的空间策略、默认配额，以及新建空间时会套用什么。',
        q1: '新建空间时会套用哪些默认设置？',
        q2: '怎样限制一个人能创建多少个空间？',
        q3: '空间的默认存储配额是多少？'
      },
      'system-global-users': {
        description: '我可以帮你查看平台用户、说明角色，以及怎样停用或调整账号。',
        q1: '平台上现在有哪些用户？',
        q2: '怎样停用或调整一个用户的权限？',
        q3: '系统管理员和普通用户差在哪里？'
      },
      'system-global-access': {
        description: '我可以说明登录、注册和访问控制这些全局开关各自管什么。',
        q1: '这些访问控制开关分别限制什么？',
        q2: '怎样关闭开放注册或限制登录方式？',
        q3: '改完这些开关要重启服务吗？'
      },
      'system-global': {
        description: '我可以帮你看这套部署的全局配置、用户与空间，以及安全相关开关。',
        q1: '这套部署的全局配置有哪些？',
        q2: '怎样管理平台上的用户和空间？',
        q3: '安全相关的开关分别管什么？'
      },
      system: {
        description: '我可以告诉你当前版本、组件状态，以及升级前建议核对什么。',
        q1: '当前版本是什么，最近更新了哪些内容？',
        q2: '怎样查看这次部署的组件状态？',
        q3: '升级前需要检查或备份什么？'
      },
      websearch: {
        description: '我可以帮你看已接入的搜索服务，并说明怎样给智能体加上联网搜索。',
        q1: '现在配置了哪些网页搜索服务？',
        q2: '怎样给智能体加上联网搜索？',
        q3: '搜索用的密钥要填在哪里？'
      },
      sandbox: {
        description: '我可以说明沙箱用来跑什么、怎样加配置，以及脚本失败时要检查哪些项。',
        q1: '沙箱是干什么用的？',
        q2: '怎样新增一套沙箱配置？',
        q3: '智能体跑脚本失败时，要检查沙箱的哪些设置？'
      },
      storage: {
        description: '我可以说明文件存在哪里、怎样改到对象存储，以及配额用完怎么办。',
        q1: '上传的文件现在存在哪里？',
        q2: '怎样改成对象存储？',
        q3: '存储配额用完了会怎样？'
      },
      parser: {
        description: '我可以帮你看默认解析引擎、哪些格式需要换解析器，以及失败时该查哪里。',
        q1: '当前默认用哪个文档解析引擎？',
        q2: '哪些文件格式需要换解析器？',
        q3: '文档解析失败时通常要改哪里？'
      },
      vectorstore: {
        description: '我可以说明当前向量检索引擎、换引擎的影响，以及怎样检查是否正常。',
        q1: '当前用的是哪套向量检索引擎？',
        q2: '换引擎会影响已经建好的知识库吗？',
        q3: '怎样检查检索引擎是否工作正常？'
      },
      ollama: {
        description: '我可以指导你连接本机 Ollama，并把拉下来的模型加到这个空间。',
        q1: '怎样连接本机的 Ollama？',
        q2: '连上之后要怎样把模型加到空间里？',
        q3: 'Ollama 连不上时通常要检查什么？'
      },
      chathistory: {
        description: '我可以说明对话历史检索开了没有、能搜到什么，以及怎样建索引。',
        q1: '对话历史检索现在开了吗？',
        q2: '开启后能搜索到哪些历史内容？',
        q3: '怎样给历史对话建立索引？'
      },
      members: {
        description: '我可以帮你看成员和角色、说明邀请方式，以及各角色能做什么。',
        q1: '这个空间现在有哪些成员、分别是什么角色？',
        q2: '怎样邀请新成员加入？',
        q3: '管理员和普通成员的权限差在哪里？'
      },
      tenant: {
        description: '我可以帮你看这个空间的名称、配额和基本信息，以及哪些可以改。',
        q1: '这个空间的名称和存储配额是多少？',
        q2: '怎样修改空间名称或描述？',
        q3: '存储快用完时会有什么影响？'
      },
      envvars: {
        description: '我可以说明这些环境变量会用在哪里，以及个人变量和工作区变量的区别。',
        q1: '这些环境变量会用在哪些技能或智能体上？',
        q2: '怎样安全地填写我自己的密钥？',
        q3: '工作区变量和我个人的变量有什么区别？'
      },
      assistant: {
        description: '我可以说明助手入口、权限等级，以及它能代你做什么、不能做什么。',
        q1: '助手的权限等级分别意味着什么？',
        q2: '怎样把助手入口放到侧栏或右下角？',
        q3: '助手能替我改设置或删除内容吗？'
      },
      userprofile: {
        description: '我可以帮你查看和修改账号资料，并说明登录信息改动后会发生什么。',
        q1: '我的账号信息在哪里改？',
        q2: '怎样修改头像、昵称或密码？',
        q3: '改完账号信息后需要重新登录吗？'
      },
      general: {
        description: '我可以帮你看清界面、语言和主题这些个人偏好，以及它们会影响哪些地方。',
        q1: '这些个人偏好分别会影响哪些界面？',
        q2: '语言和主题要怎么改？',
        q3: '还有哪些个人设置建议先配好？'
      },
      fallback: {
        description: '我可以解释这个设置页是做什么的，改动会影响什么，以及哪些项建议先配好。',
        q1: '这个设置页是做什么的？',
        q2: '改这里会影响哪些功能？',
        q3: '有哪些项建议先配好？'
      }
    },
    welcomeDescriptions: {
      knowledgeBases: '我可以帮你选择知识库类型、整理资料，找到适合当前问题的知识来源。',
      knowledgeBase: '我可以概括这些文档在讲什么，找出最近的更新，以及还没解析完的文件。',
      document: '我可以提炼文档要点、整理操作步骤，也能把内容转成常见问答。',
      faq: '我可以检查问答覆盖范围、找出重复问题，帮你把答案写得更清楚。',
      wiki: '我可以梳理页面内容、追溯引用来源，帮你找出需要补充或更新的地方。',
      agents: '告诉我想完成什么，我可以帮你创建智能体，搭配模型、知识库和工具。',
      automation: '我可以把重复工作安排成定时任务，也能查看运行结果、调整执行计划。',
      skills: '告诉我任务目标，我可以帮你查找、添加技能，并配置到合适的智能体。',
      mcp: '我可以帮你查找和接入 MCP 服务，了解可用工具，并配置给智能体使用。',
      browser: '我可以指导你连接浏览器，了解适合自动操作的任务和所需授权。',
      model: '我可以帮你接入模型、比较用途，检查配置是否适合当前任务。',
      chat: '我可以概括这次对话做了什么，核对最后一轮回答，并帮你想好还能接着问什么。',
      message: '我可以追溯这条回答的来源、核对关键信息，帮你整理成可复用的内容。',
      artifacts: '我可以按时间和类型整理这些文件，找到它们来自哪次对话，以及怎样让智能体把结果保存下来。',
      organizations: '我可以帮你看清各共享空间里有哪些知识库和智能体，以及怎样创建、加入或邀请成员。'
    },
    help: {
      label: '助手说明',
      title: '小知助手能做什么',
      identity: '助手以你的身份工作。它能看到和修改的范围，与你在这个空间里的角色一致，不会超出你的权限。',
      page: '打开后会附带当前页面，可以据此梳理内容、配置智能体和自动化，或代为填写表单。它不会替你点击按钮或保存。',
      access: '输入框下方可以切换权限：只读、修改前确认、自动执行。删除始终需要你确认。管理员限制的最高等级无法突破。'
    },
    layout: {
      dock: '固定在右侧',
      float: '改为悬浮'
    }
  },
  preview: {
    loading: '正在加载文档预览...',
    loadFailed: '加载文档预览失败',
    retry: '重试',
    unsupported: '该文件类型暂不支持在线预览',
    unsupportedHint: '请下载文件后使用本地应用查看',
    zoomIn: '放大',
    zoomOut: '缩小',
    fullscreen: '全屏预览',
    exitFullscreen: '退出全屏',
    htmlRendered: '渲染预览',
    htmlSource: '查看源码',
    audioNotSupported: '您的浏览器不支持音频播放',
    videoNotSupported: '您的浏览器不支持视频播放'
  },
  organization: {
    owner: '创建者',
    roleUpdated: '角色已更新',
    roleUpdateFailed: '更新角色失败',
    createdByMe: '我创建的',
    joinedByMe: '我加入的',
    share: {
      title: '共享到共享空间',
      selectOrg: '选择共享空间',
      selectOrgPlaceholder: '请选择要共享的共享空间',
      permission: '权限',
      permissionTip: '可编辑权限允许成员修改知识库内容，只读权限仅允许检索和问答',
      shareSuccess: '已共享',
      shareFailed: '共享失败',
      unshareSuccess: '已取消共享',
      unshareFailed: '取消共享失败',
      sharedTo: '已共享到',
      noShares: '尚未共享到任何共享空间',
      searchPlaceholder: '搜索共享空间…',
      loading: '加载中…',
      emptySearch: '未找到匹配「{q}」的共享空间',
      addShareDialogTitle: '共享到共享空间',
      unshareAction: '取消共享',
      sharedFrom: '来自',
      permissionReadonly: '只读',
      permissionEditable: '可编辑',
      columns: {
        space: '共享空间',
        permission: '权限',
        sharedAt: '共享时间',
        operations: '操作'
      }
    },
    settings: {
      pendingJoinRequestsBadge: '有待审批的加入申请'
    },
    role: {
      admin: '管理员',
      editor: '编辑',
      viewer: '只读'
    },
    join: {
      title: '加入共享空间'
    }
  },
  promptTemplate: {
    noTemplates: '暂无模板',
    selectTemplate: '选择模板',
    useTemplate: '使用模板',
    resetDefault: '恢复默认',
    default: '默认',
    withKnowledgeBase: '知识库',
    withWebSearch: '网络搜索'
  },
  mcpServiceDialog: {
    addTitle: '添加 MCP 服务',
    addDesc: '连接外部 MCP 服务，智能体即可调用其中的工具。',
    editTitle: '编辑 MCP 服务',
    basicSection: '基本信息',
    connectionSection: '连接配置',
    enableServiceDesc: '关闭后该服务不会被调用',
    unitSecond: '秒',
    name: '服务名称',
    namePlaceholder: '请输入服务名称',
    transportType: '传输类型',
    serviceUrl: '服务 URL',
    serviceUrlPlaceholder: 'https://example.com/mcp',
    enableService: '启用服务',
    authConfig: '认证配置',
    authType: '认证方式',
    authTypeNone: '无 / 自定义 Header',
    authTypeApiKey: 'API Key / Token',
    authTypeOAuth: 'OAuth 2.0（首次连接授权）',
    oauthScopes: 'Scopes（可选，空格分隔）',
    oauthClientId: 'Client ID（可选）',
    oauthClientIdDesc: '填写在授权服务器预先注册的客户端；留空则自动进行动态客户端注册。更换 Client ID 时请同时更新 Client Secret。',
    oauthClientSecret: 'Client Secret（可选）',
    oauthAuthorization: '授权状态',
    oauthAuthorized: '已授权',
    oauthRefreshable: 'Token 已过期，将在下次使用时自动刷新',
    oauthUnauthorized: '未授权',
    oauthAuthorize: '去授权',
    oauthReauthorize: '重新授权',
    oauthRevoke: '撤销授权',
    oauthAuthorizeHint: '点击「去授权」会先自动保存当前配置，再发起授权（每个用户独立授权）。',
    apiKeyHeader: '请求头名称',
    apiKeyHeaderDesc: '留空默认 X-API-Key。Bearer 方式请填 Authorization，并在下方密钥值中写 “Bearer <token>”；需要裸 token 时填 Authorization 并直接填入 token。',
    credentialValue: '密钥值 / Token',
    optional: '可选',
    advancedConfig: '高级配置',
    timeoutSec: '超时时间(秒)',
    codeImport: {
      toggle: '从代码导入',
      hint: '粘贴标准 mcpServers JSON 配置，自动填充表单',
      parse: '解析并填充',
      editOverwriteHint: '导入会覆盖当前表单内容（不影响已保存的凭证，需点保存生效）',
      toasts: {
        filled: '已填充表单，请检查后保存',
        multipleServers: '检测到多个服务，已导入第一个：{name}'
      },
      errors: {
        empty: '请先粘贴配置内容',
        invalidJson: '无法解析，请检查 JSON 格式',
        noServer: '未找到 MCP 服务配置',
        missingUrl: '配置缺少 url',
        stdioUnsupported: '暂不支持 stdio（command/args）配置，请使用带 url 的远程配置'
      }
    },
    customHeaders: {
      label: '自定义请求头（可选）',
      desc: '附加到每次 MCP 请求的 HTTP 请求头，常用于企业网关鉴权、链路追踪等场景。',
      add: '添加请求头',
      keyPlaceholder: 'Header 名称',
      valuePlaceholder: 'Header 值'
    },
    toasts: {
      updated: 'MCP 服务已更新',
      updateFailed: '更新 MCP 服务失败',
      authorized: '授权成功',
      authorizeFailed: '发起授权失败',
      revoked: '已撤销授权',
      revokeFailed: '撤销失败'
    },
    rules: {
      nameRequired: '请输入服务名称',
      transportRequired: '请选择传输类型',
      urlRequired: '请输入服务 URL',
      urlInvalid: '请输入有效的 URL'
    }
  },
  mcpMetadata: {
    searchTools: '搜索工具名称或描述',
    retry: '重试',
    details: '详情',
    description: '描述',
    parameters: '参数',
    required: '必填',
    fullSchema: '完整定义',
    noDescription: '没有描述',
    noParameters: '没有参数定义',
    enabled: '启用工具',
    approval: '调用需审批',
    noTools: '没有匹配的工具',
    next: '下一页',
    policyLoadFailed: '工具策略读取失败，请重试后再修改。',
    policySaveFailed: '工具设置保存失败',
    tools: 'Tools 清单',
    cacheHint: '尚未同步时会自动连接并保存完整描述；之后只在刷新时访问 MCP 服务。',
    fetch: '重新拉取',
    fetching: '正在连接并拉取 Tools…',
    toolCount: '{count} 个工具',
    stale: '连接或认证配置已改变。以下是旧目录，重新同步后才能供模型使用。',
    notSynced: '尚未同步工具。连接并拉取后，会保存完整描述和参数定义。',
    syncRequired: '请先连接并拉取 Tools，同步后的目录才能给模型使用。',
    syncedAt: '同步时间：',
    serverDocumentation: '服务端原始说明',
    noServerDocumentation: '该 MCP Server 的 initialize 未返回 instructions / serverInfo.description（均为可选字段）。工具说明在下方各工具的 description 里。',
    policyHint: '工具开关与审批设置即时保存；刷新目录不会覆盖这些设置。',
    columnTool: '工具',
    columnEnabled: '启用',
    columnApproval: '需审批',
    failed: '工具目录读取失败',
    setupProgress: 'MCP 配置步骤',
    connection: '连接配置',
    toolsAndUsage: '工具与用途说明',
    previous: '上一步',
    usage: '服务用途',
    usageHint: '模型先读取服务用途，再按需加载具体工具。以下内容由你维护，刷新不会覆盖。',
    usageInstructions: '使用说明',
    instructionsPlaceholder: '简要说明服务用途、适用场景和关键使用约束。',
    generateUsage: 'AI 生成',
    generateHint: '根据已同步且启用的 Tools 生成精简说明，填入后可编辑，保存后生效。',
    instructionsRequired: '使用说明不能为空',
    generated: '已生成，请检查后保存',
    generateFailed: '生成失败，请确认 Tools 已同步且已配置可用的对话模型后重试。'
  },
  ollamaSettings: {
    installed: {
      title: '已下载的模型',
      desc: '已安装在 Ollama 中的模型列表'
    },
    download: {
      title: '下载新模型'
    },
    address: {
      desc: '本地 Ollama 服务的 API 地址，由系统自动检测。如需修改，请在 .env 配置文件中设置'
    },
    status: {
      desc: '自动检测本地 Ollama 服务是否可用。如果服务未运行或地址配置错误，将显示"不可用"状态'
    }
  },
  modelSettings: {
    moreActions: '更多操作',
    title: '模型配置',
    copySuffix: ' 副本',
    builtinTag: '内置',
    confirmDelete: '确定删除模型「{name}」吗？',
    debug: {
      reasoningEffort: '思考强度',
      reasoningEffortDesc: '按模型目录上报的等级发送 reasoning_effort',
      title: '模型测试',
      description: '使用已保存的模型配置发送真实请求；编辑中的修改需保存后才会生效',
      groupModel: '选择模型',
      groupInput: '测试输入',
      groupResult: '运行结果',
      modelType: '模型类型',
      model: '模型',
      modelPlaceholder: '请选择要测试的模型',
      noModelsForType: '当前类型暂无已添加模型',
      query: '输入内容',
      queryPlaceholder: '输入要发送给模型的内容',
      embeddingInput: '待向量化文本',
      embeddingPlaceholder: '输入要生成 Embedding 的文本',
      vlmPrompt: '图片提示词',
      vlmPromptPlaceholder: '例如：请详细描述这张图片',
      documents: '候选文档',
      documentsPlaceholder: '每行输入一个候选文档',
      documentsHint: '每个非空行会作为一个独立文档发送给 ReRank 模型',
      imageFile: '图片文件',
      similarityMode: '相似度',
      similarityQuery: '查询文本',
      similarityQueryPlaceholder: '输入一条查询，例如：草地上奔跑的狗',
      similarityCandidates: '候选文本',
      similarityCandidatesPlaceholder: '每行输入一个候选文本',
      similarityHint: '查询按检索查询方式向量化，候选按文档方式向量化，与线上检索一致；结果按余弦相似度从高到低排列',
      similarityImage: '候选图片（可选）',
      similarityImageCandidate: '图片',
      audioFile: '音频文件',
      chooseFile: '选择文件',
      parameters: '请求参数',
      systemPrompt: 'System Prompt',
      systemPromptPlaceholder: '可选，输入系统提示词',
      run: '运行测试',
      copyResult: '复制结果',
      history: '历史记录',
      runLabel: '第 {n} 次运行',
      success: '调用成功',
      failed: '调用失败',
      rawResponse: '响应内容',
      requestPreview: '请求预览',
      requestFailed: '模型测试请求失败',
      metrics: {
        api: '协议',
        thinkingFormat: '思考格式',
        requestedReasoningEffort: '请求思考强度',
        dimension: '向量维度',
        resultCount: '结果数量',
        answerChars: '回答字符数',
        reasoningChars: '推理字符数',
        reasoningReturned: '返回推理内容',
        textChars: '转写字符数',
        segmentCount: '分段数量'
      }
    },
    usage: {
      title: '模型无法删除',
      description: '模型「{name}」仍被以下配置引用。请先打开对应配置并更换模型，再重新删除。',
      knowledgeBases: '知识库（{count}）',
      agents: '智能体（{count}）',
      openConfiguration: '打开配置',
      truncated: '仅显示前 {shown} 个，共 {total} 个',
      longTermMemory: '长期记忆'
    },
    builtinModels: {
      title: '内置模型',
      description: '内置模型对所有空间可见，敏感信息会被隐藏，且不可编辑或删除。',
      descriptionAdmin: '内置模型对所有空间可见。系统管理员可编辑配置和凭据；删除仍由部署配置管理。',
      viewGuide: '查看内置模型管理指南'
    },
    toasts: {
      nameRequired: '模型名称不能为空',
      nameTooLong: '模型名称不能超过100个字符',
      displayNameTooLong: '显示名称不能超过100个字符',
      baseUrlRequired: 'Remote API 类型必须填写 Base URL',
      baseUrlInvalid: 'Base URL 格式不正确，请输入有效的 URL',
      dimensionInvalid: 'Embedding 模型必须填写有效的向量维度（128-4096）',
      updated: '模型已更新',
      added: '模型已添加',
      saveFailed: '保存模型失败',
      deleted: '模型已删除',
      deleteFailed: '删除模型失败',
      builtinCannotEdit: '内置模型不能编辑',
      linkedModelMissing: '没有找到助手链接的模型，它可能已被删除',
      builtinCannotDelete: '内置模型不能删除',
      builtinCannotCopy: '内置模型不能复制',
      copied: '模型已复制',
      copyFailed: '复制模型失败'
    },
    asr: {
      title: 'ASR 语音模型',
      desc: '配置用于语音识别和音频转录的语音转文本模型（如 OpenAI Whisper）',
      empty: '暂无 ASR 语音模型'
    },
    vllm: {
      title: 'VLLM 视觉模型',
      desc: '配置用于视觉理解和多模态的视觉语言模型',
      empty: '暂无 VLLM 视觉模型'
    },
    rerank: {
      title: 'ReRank 模型',
      desc: '配置用于结果重排序的模型',
      empty: '暂无 ReRank 模型'
    },
    embedding: {
      title: 'Embedding 模型',
      desc: '配置用于文本向量化的嵌入模型',
      empty: '暂无 Embedding 模型'
    },
    chat: {
      title: '对话模型',
      desc: '配置用于对话的大语言模型',
      empty: '暂无对话模型'
    },
    source: {
      remote: 'Remote',
      openaiCompatible: 'OpenAI兼容',
      custom: '自定义'
    },
    actions: {
      addModel: '添加模型',
      debugModel: '模型测试'
    },
    typeShort: {
      chat: '对话',
      embedding: 'Embedding',
      rerank: 'ReRank',
      vllm: '视觉',
      asr: '语音'
    }
  },
  mcpSettings: {
    addUsageInstructions: '添加使用说明',
    noUsageInstructions: '尚未填写使用说明',
    title: 'MCP 服务管理',
    description: '管理外部 MCP (Model Context Protocol) 服务，在 Agent 模式下调用外部工具和资源',
    enabled: '已启用',
    disabled: '已禁用',
    addService: '添加服务',
    empty: '暂无 MCP 服务',
    deleteConfirmBody: '确定要删除 MCP 服务"{name}"吗？此操作无法撤销。',
    unnamed: '未命名',
    builtin: '内置',
    toolCount: '{count} 个工具',
    toolsNotSynced: '尚未同步工具',
    toolsStale: '需重新同步',
    toasts: {
      loadFailed: '加载 MCP 服务列表失败',
      enabled: '已启用 MCP 服务',
      disabled: '已禁用 MCP 服务',
      updateStateFailed: '更新 MCP 服务状态失败',
      linkedServiceMissing: '没有找到助手链接的 MCP 服务，它可能已被删除',
      deleted: 'MCP 服务已删除',
      deleteFailed: '删除 MCP 服务失败'
    }
  },
  conversationSettings: {
    maxTokens: {
      desc: '生成回答的最大Token数量'
    },
    temperature: {
      desc: '控制模型输出的随机性，0最确定，1最随机'
    },
    systemPrompt: {
      desc: '用于普通模式对话的系统级Prompt'
    },
    contextTemplate: {
      desc: '用于普通模式下基于检索结果生成回答的Prompt模板'
    },
    rerankModel: {
      desc: '用于搜索结果重排序的模型（可选）'
    },
    chatModel: {
      desc: '用于总结和摘要的大语言模型'
    },
    rewritePrompt: {
      desc: '控制问题改写的系统提示词'
    },
    fallbackPrompt: {
      desc: '当选择模型兜底时使用的提示模板'
    },
    fallbackResponse: {
      desc: '当兜底策略为固定回复时返回的文本'
    },
    fallbackStrategy: {
      desc: '检索无结果时采用的处理方式'
    },
    enableQueryExpansion: {
      desc: '召回不足时调用大模型生成扩展查询（增加时延与成本）'
    },
    enableRewrite: {
      desc: '多轮对话自动改写问题以获得更优召回'
    },
    rerankThreshold: {
      desc: '重排序阶段的最低得分阈值'
    },
    rerankTopK: {
      desc: '重排序后进入答案生成的文档数量'
    },
    vectorThreshold: {
      desc: '向量召回的最低相似度阈值'
    },
    keywordThreshold: {
      desc: '关键词检索的最低得分阈值'
    },
    embeddingTopK: {
      desc: '向量召回阶段保留的文档数量'
    },
    maxRounds: {
      desc: '用于多轮上下文和问题改写的历史轮数'
    },
    models: {
      chatGroupLabel: '思考 / 对话模型'
    }
  },
  agentSettings: {
    systemPrompt: {
      desc: '配置 Agent 的系统提示词，支持占位符模板。占位符会在运行时自动替换为实际内容。'
    },
    allowedTools: {
      desc: '当前 Agent 可使用的工具列表'
    },
    temperature: {
      desc: '控制模型输出的随机性，0 最确定，1 最随机'
    },
    rerankModel: {
      desc: '搜索结果重排序，统一不同来源的相关度分数'
    },
    thinkingModel: {
      desc: '用于 Agent 推理和规划的 LLM 模型'
    },
    maxIterations: {
      desc: '限制 Agent 单次任务的推理步数。选「不限制」时会一直跑到模型自然结束或你手动停止。'
    },
    modelRecommendation: {
      title: '模型推荐'
    }
  },
  uploadTasks: {
    panelLabel: '上传任务',
    titleUploading: '正在上传 {done}/{total}',
    titleParsing: '正在解析 {done}/{total}',
    titleDone: '全部完成',
    titleDoneWithIssues: '{ok} 个完成，{bad} 个未成功',
    titleCancelled: '上传已取消',
    destination: '上传至「{name}」',
    destinationMany: '上传至 {count} 个知识库',
    remaining: '剩余约 {time}',
    hintUploading: '上传完成前请不要关闭或刷新页面',
    hintParsing: '文件已全部上传，解析在后台继续，可以放心离开此页面',
    filterAll: '全部',
    filterIssues: '未成功',
    phaseWaiting: '等待上传',
    phaseSaving: '正在保存…',
    phasePending: '排队解析',
    phaseReady: '已完成',
    phaseParseFailed: '解析失败',
    phaseDuplicate: '知识库中已有相同文件',
    phaseCancelled: '已取消',
    cancel: '取消',
    cancelAll: '全部取消',
    retry: '重试',
    retryFailed: '重试 {count} 个',
    open: '查看',
    collapse: '收起',
    expand: '展开',
    close: '关闭',
    closeConfirm: '关闭后将取消剩余 {count} 个文件的上传',
    closeConfirmOk: '取消上传',
    closeConfirmKeep: '继续上传',
    legend: {
      ready: '可检索',
      active: '处理中',
      waiting: '等待中',
      failed: '失败',
      duplicate: '已存在'
    },
    eta: {
      seconds: '{n} 秒',
      minutes: '{n} 分钟',
      hours: '{n} 小时'
    }
  },
  upload: {
    uploadDocument: '上传文档',
    uploadFolder: '上传文件夹',
    onlineEdit: '在线编辑',
    deleteRecord: '删除记录'
  },
  time: {
    today: '今天',
    yesterday: '昨天',
    last7Days: '近7天',
    last30Days: '近30天',
    lastYear: '近1年',
    earlier: '更早',
    pinned: '已置顶'
  },
  platform: {
    multimodalParsing: '多模态文档解析',
    hybridSearchEngine: '混合检索 + 知识图谱',
    ragQandA: 'ReAct 智能体问答',
    independentTenant: '独立空间',
    fullApiAccess: '完整 API 访问',
    knowledgeBaseManagement: '知识库管理',
    loginShowcase: {
      carouselLabel: '任我行知识库功能示意',
      switchLabel: '切换功能主题',
      pause: '暂停轮播与流光',
      play: '播放轮播与流光',
      reducedMotion: '已按减少动态效果设置停止自动播放',
      labels: {
        query: '自然语言提问',
        sourceHit: '命中原文',
        citedAnswer: '回答附有引用',
        sourceMaterial: '来源资料',
        productKnowledge: '产品知识',
        delivery: '实施交付',
        customerService: '客户服务',
        documents: '文档资料',
        webContent: '网页内容',
        existingKnowledge: '已有知识',
        knowledgeEntry: '统一知识入口',
        materialsReceived: '资料已汇聚',
        contentChange: '内容变化',
        knowledgeReview: '知识评审',
        knowledgeUpdate: '知识更新',
        updateConfirmed: '本次更新已确认'
      },
      themes: {
        review: {
          title: '知识变化，及时更新',
          description: '经过知识评审，让资料持续产生价值',
          summary: '内容变更先经过评审确认，再进入知识库更新对应内容。',
          mobile: '内容变化 → 知识评审 → 知识更新',
          tab: '评审更新'
        },
        intake: {
          title: '企业资料，一处汇聚',
          description: '连接文档、网页与现有知识平台',
          summary: '文档、网页和已有知识汇入同一个知识入口，资料接收后确认汇聚。',
          mobile: '文档 / 网页 / 已有知识 → 统一入口',
          tab: '资料汇聚'
        },
        organization: {
          title: '分散文档，有序关联',
          description: '按主题展开资料，连接相关的知识',
          summary: '来源资料依次展开为产品知识、实施交付和客户服务三个主题。',
          mobile: '来源资料 → 产品 / 实施 / 服务知识',
          tab: '知识组织'
        },
        query: {
          title: '每次提问，都有依据',
          description: '从自然语言提问，直达有出处的回答',
          summary: '问题进入检索，命中原文，回答与引用同时显现。',
          mobile: '提问 → 命中原文 → 回答附有引用',
          tab: '问答溯源'
        }
      }
    }
  },
  font: {
    uiFont: '界面字体',
    uiFontDescription: '用于菜单、正文、按钮等界面大部分文字的字体',
    monoFont: '代码字体',
    monoFontDescription: '用于代码块、终端命令、API 密钥、文件路径等技术内容，每个字符等宽显示，避免 0/O、1/l 混淆',
    selectFont: '选择字体',
    sansPreview: '示例 Sample 字体 Font — Aa Gg Oo 0123',
    monoPreview: 'const msg = \'Hello\'; // 0O1l',
    fontSize: '字体大小',
    fontSizeDescription: '整体缩放界面（文字、图标、间距等），切换后立即生效',
    size: {
      small: '小',
      normal: '正常',
      large: '大'
    },
    mono: {
      system: '系统默认',
      menlo: 'Menlo',
      monaco: 'Monaco',
      consolas: 'Consolas',
      cascadia: 'Cascadia Code',
      'dejavu-mono': 'DejaVu Sans Mono',
      'liberation-mono': 'Liberation Mono',
      monospace: '通用等宽'
    },
    sans: {
      system: '系统默认',
      pingfang: '苹方 PingFang SC',
      georgia: 'Georgia 衬线',
      yahei: '微软雅黑 Microsoft YaHei',
      times: 'Times New Roman 衬线',
      'noto-cjk': 'Noto Sans CJK',
      'dejavu-serif': 'DejaVu Serif 衬线',
      'sans-serif': '通用无衬线'
    }
  },
  theme: {
    theme: '主题模式',
    themeDescription: '选择界面的显示主题，支持跟随系统自动切换',
    light: '浅色',
    dark: '深色',
    system: '跟随系统',
    selectTheme: '选择主题'
  },
  general: {
    title: '常规设置',
    personalSettings: '个人设置',
    description: '配置语言、外观等基础选项',
    close: '关闭设置'
  },
  language: {
    zhCN: '简体中文',
    zhTW: '繁體中文',
    enUS: 'English',
    ruRU: 'Русский',
    koKR: '한국어',
    jaJP: '日本語',
    selectLanguage: '选择语言',
    language: '语言',
    languageDescription: '选择界面显示语言',
    languageSaved: '语言设置已保存'
  },
  model: {
    modelName: '模型名称',
    defaultTag: '默认',
    addModelInSettings: '前往全局设置添加模型',
    loadFailed: '加载模型列表失败',
    selectModelPlaceholder: '请选择模型',
    builtinTag: '内置',
    editor: {
      legacyLocalUnavailable: '旧 Ollama 服务管理已停用。原记录保留；如需使用本机模型，请切换为 API 并填写 OpenAI 兼容服务地址。',
      maxOutputTokensLabel: '最大输出 tokens',
      maxOutputTokensPlaceholder: '留空使用目录默认',
      maxOutputTokensDesc: '单次回复的输出上限。留空则沿用目录中该模型的默认值。',
      addTitle: '添加模型',
      editTitle: '编辑模型',
      sectionType: '模型类型',
      typeLabel: '模型类型',
      sectionSource: '模型来源',
      sectionProvider: '接入配置',
      sectionAdvanced: '高级选项',
      sourceLabel: '模型来源',
      sourceRemote: 'API',
      baseUrlLabel: 'Base URL',
      displayNameLabel: '显示名称（可选）',
      displayNamePlaceholder: '例如：客服问答模型',
      displayNameDesc: '仅用于界面展示，实际调用仍使用上面的模型名称。',
      baseUrlPlaceholder: '例如：https://api.openai.com/v1',
      baseUrlPlaceholderVllm: '例如：http://localhost:11434/v1',
      baseUrlPlaceholderAsr: '例如：https://api.openai.com/v1',
      apiKeyOptional: 'API Key（可选）',
      apiKeyPlaceholder: '输入 API Key',
      customHeadersLabel: '自定义请求头（可选）',
      customHeadersDesc: '调用远程模型 API 时附加的 HTTP 请求头，常用于企业网关鉴权、链路追踪等场景；Authorization、Content-Type 等保留头会被自动忽略。',
      customHeadersAdd: '添加请求头',
      customHeadersKeyPlaceholder: 'Header 名称',
      customHeadersValuePlaceholder: 'Header 值',
      testing: '测试中...',
      testConnection: '测试连接',
      dimensionLabel: '向量维度',
      dimensionPlaceholder: '例如：1536',
      dimensionOverrideLabel: '自定义输出维度',
      dimensionOverrideDesc: '仅在确认该模型支持 dimensions 参数时开启；默认只使用检测到的实际维度。',
      supportsVisionLabel: '支持视觉/多模态',
      supportsVisionDesc: '模型是否支持图片等多模态输入',
      embeddingImageInputLabel: '图片输入',
      embeddingImageInputDesc: '模型能把图片编码到与文本相同的向量空间。目录内的模型自动识别，自定义模型需手动声明',
      contextWindowLabel: '上下文窗口',
      contextWindowPlaceholder: '填写厂商公布的总上下文窗口',
      contextWindowDesc: '该模型一次请求的总上下文窗口。高级 spec 优先于此处填写值；留空且未配置 spec 时显示未知。请按厂商文档填写真实值，智能体会预留输出预算和压缩余量。',
      contextWindowUnknown: '未知',
      contextWindowTokens: '{count} tokens',
      maxConcurrencyLabel: '后台并发上限',
      maxConcurrencyPlaceholder: '0 表示使用全局默认',
      maxConcurrencyDesc: '限制文档入库/富化等后台任务对该模型的并发调用数（按模型全副本共享）。0 或留空表示沿用全局默认；不影响交互式对话。',
      fillModelAndUrl: '请先填写模型标识和 Base URL',
      remoteBaseUrlRequired: 'Remote API 类型必须填写 Base URL',
      unsupportedModelType: '不支持的模型类型',
      saveAndClose: '保存并关闭',
      testDraftHint: '使用当前填写的连接配置，无需提前保存。',
      testDraftEditHint: '使用当前填写的连接配置；API Key 使用已单独保存的值。',
      testStale: '配置已修改，请重新测试。',
      connectionSuccess: '连接成功',
      connectionFailed: '连接失败',
      connectionConfigError: '连接失败，请检查配置',
      providerLabel: '服务商',
      providerPlaceholder: '选择模型服务商',
      providerDocs: '查看 {provider} 的模型文档',
      validation: {
        extraFieldRequired: '请填写 {name}',
        modelNameRequired: '请输入模型名称',
        modelNameEmpty: '模型名称不能为空',
        modelNameMax: '模型名称不能超过100个字符',
        baseUrlRequired: '请输入 Base URL',
        baseUrlEmpty: 'Base URL 不能为空',
        baseUrlInvalid: 'Base URL 格式不正确，请输入有效的 URL'
      },
      modelNamePlaceholder: {
        remote: '例如：gpt-4, claude-3-opus',
        remoteVllm: '例如：gpt-4-vision-preview',
        remoteAsr: '例如：whisper-1'
      },
      description: {
        chat: '配置用于对话的大语言模型',
        embedding: '配置用于文本向量化的嵌入模型',
        rerank: '配置用于结果重排序的模型',
        vllm: '配置用于视觉理解和多模态的视觉语言模型',
        asr: '配置用于语音识别和音频转录的语音转文本模型',
        default: '配置模型信息'
      },
      advanced: {
        toggle: '高级',
        compat: {
          label: '协议兼容覆盖（JSON）',
          placeholder: '{\'{\'} "max_tokens_field": "max_tokens" {\'}\'}',
          desc: '只在接口与目录默认值不一致时填写，只写需要改的字段。留空表示不覆盖。',
          docLink: '查看字段说明',
          invalid: 'JSON 格式不正确',
          mustBeObject: '必须是 JSON 对象'
        },
        legacyThinking: {
          label: '思考参数格式（旧配置）',
          catalog: '遵循目录默认（推荐）',
          none: '不写入思考参数',
          desc: '此模型仍带有旧版 thinking_control 设置。选择「遵循目录默认」后由目录决定思考参数的写法。'
        },
        remoteModelName: {
          label: '远端模型名',
          placeholder: '留空与模型名相同',
          desc: '实际发送给厂商的模型 ID，与上面的模型名不同时填写。'
        },
        api: {
          label: '协议覆盖',
          auto: '自动（按厂商 / URL 推断）',
          desc: '强制使用指定的请求协议；一般无需修改。'
        }
      },
      resolved: {
        title: '实际调用方式',
        empty: '填写厂商与模型名后，这里会显示这个模型将被怎样调用',
        failed: '解析失败',
        protocol: '请求协议',
        catalog: '能力来源',
        catalogedYes: '内置模型档案',
        catalogedNo: '厂商通用默认（未收录此模型）',
        endpoint: '请求地址',
        thinkingFormat: '思考开关传参',
        thinkingLevels: '可选思考强度',
        noThinking: '该模型不支持思考'
      },
      catalog: {
        reasoning: '推理',
        vision: '视觉',
        hint: '可从厂商内置目录选择，也可直接输入自定义模型名。'
      }
    }
  },
  error: {
    networkError: '网络错误，请检查您的网络连接',
    invalidCredentials: '用户名或密码错误',
    tokenRefreshFailed: 'Token刷新失败',
    pleaseRelogin: '请重新登录',
    fileSizeExceeded: '文件大小不能超过 {size}M！',
    unsupportedFileType: '不支持的文件类型！',
    invalidImageLink: '无效的图片链接',
    tokenNotFound: '未找到登录令牌，请重新登录',
    streamFailed: '流式连接失败',
    initialization: {
      checkFailed: '检查失败',
      testFailed: '测试失败'
    },
    tenant: {
      listFailed: '获取空间列表失败',
      searchFailed: '搜索空间失败',
      getApiPrincipalConfigFailed: '获取 API 用户身份配置失败',
      updateApiPrincipalConfigFailed: '更新 API 用户身份配置失败',
      createApiPrincipalTestTokenFailed: '生成 API 测试 Token 失败',
      updateFailed: '更新空间信息失败',
      deleteFailed: '删除空间失败'
    },
    model: {
      createFailed: '创建模型失败',
      getFailed: '获取模型失败',
      updateFailed: '更新模型失败',
      deleteFailed: '删除模型失败'
    },
    auth: {
      loginFailed: '登录失败',
      registerFailed: '注册失败',
      getUserFailed: '获取用户信息失败',
      getTenantFailed: '获取空间信息失败',
      updatePreferencesFailed: '更新个性化设置失败',
      refreshTokenFailed: '刷新Token失败',
      logoutFailed: '登出失败',
      validateTokenFailed: 'Token验证失败'
    }
  },
  mcp: {
    testResult: {
      title: '测试结果: {name}'
    }
  },
  system: {
    globalSettings: {
      title: '系统设置',
      audit: {
        action: {
          'system.setting_changed': '系统设置变更',
          'system.admin_promoted': '授予系统管理员',
          'system.api_key_created': '创建平台 API Key',
          'system.api_key_revoked': '吊销平台 API Key',
          'system.admin_revoked': '回收系统管理员',
          'system.user_password_reset': '重置用户密码',
          'system.user_created': '创建用户',
          'system.queue_task_retried': '重新执行失败任务',
          'system.queue_task_deleted': '清除失败任务记录',
          'system.queue_task_run_now': '立即执行队列任务',
          'system.queue_task_cancelled': '终止队列任务',
          'system.queue_archived_purged': '清除全部失败任务'
        },
        actorRole: {
          system_admin: '系统管理员'
        }
      },
      listConfirm: {
        ssrf: {
          whitelist: {
            remove: {
              header: '移除 SSRF 白名单条目',
              body: '确认从 SSRF 白名单中移除 {entry}？移除后该条目将重新受 SSRF 防护拦截。',
              confirmBtn: '移除'
            },
            add: {
              header: '添加 SSRF 白名单条目',
              body: '确认把 {entry} 加入 SSRF 白名单？该条目匹配到的主机 / IP / 网段会绕过 SSRF 防护，可能让 Agent 访问内网服务，请仅在确知用途时添加。',
              confirmBtn: '添加'
            }
          }
        }
      },
      enumLabels: {
        auth: {
          default_tenant_mode: {
            create_personal: '自动创建个人空间',
            tenantless: '不自动创建空间'
          },
          registration_mode: {
            self_serve: '自助注册（任何人可注册）',
            invite_register: '仅限邀请注册（需有效邀请链接）',
            invite_only: '禁止注册（已有账号仍可接受邀请）'
          }
        }
      },
      keyDescriptions: {
        model: {
          max_concurrency: '后台任务（文档入库/富化）对单个模型的默认并发上限，按模型 ID 全副本共享。每次调用实时读取，修改后立即生效、无需重启。0 或负数表示关闭默认限制（各模型仍会尊重自身在模型管理里配置的上限）。仅影响后台任务，不影响交互式对话。'
        },
        asynq: {
          core_concurrency: '文档解析与手工重解析的每实例保底并发，可额外借用共享弹性池；修改后需重启。',
          postprocess_concurrency: '解析完成后的轻量收尾和富化扇出专用并发；修改后需重启。',
          enrichment_concurrency: '摘要、图片、图谱与问题生成的每实例保底并发，可额外借用共享弹性池；修改后需重启。',
          maintenance_concurrency: '数据源同步、批处理和清理任务的每实例并发，与用户面流水线硬隔离；修改后需重启。',
          shared_concurrency: '核心解析与内容富化共同使用的每实例弹性并发，由有积压的一侧自动借用；修改后需重启。',
          wiki_concurrency: '每个服务实例的 Wiki 专用 Worker 并发数，与上游任务池相互隔离。最小值为 1；修改后需重启服务进程方可生效。'
        },
        tenant: {
          max_owned_per_user: '每个非超管用户通过自助创建可拥有的最大空间数。每次创建空间时实时读取，修改后立即生效。0 表示使用内置默认值 10；负数表示完全关闭限制（不建议在公开部署使用）。',
          self_service_creation_enabled: '是否允许非超管用户主动创建空间。关闭后，普通用户只能通过邀请加入已有空间；跨空间超管仍可创建。修改后立即生效。',
          default_storage_quota_gb: '新建空间时默认分配的存储配额（GB），包含向量、原文、文本、索引等。仅在创建时读取，修改后只对之后新建的空间生效，不会回写已存在的空间。0 或负数表示使用内置默认值 10GB。',
          default_storage_quota_mb: '包括注册自动创建的个人空间。正数优先于 GB 设置；0 或负数沿用 GB 设置。每个设置按数据库、环境变量、内置默认值的顺序读取，仅影响之后新建的空间。',
          auto_create_api_key: '为新空间自动生成 full_access API Key，并在创建响应中返回明文 token。仅用于兼容依赖旧行为的集成；默认关闭，建议通过 API Key 管理显式创建。',
          auto_accept_invitation: '开启后，空间管理员通过邮箱邀请已注册用户时，对方会立即成为成员，不再经过收件箱确认。关闭时保持「发出邀请 → 被邀请人确认」流程。修改后立即生效。'
        },
        sandbox: {
          docker_enabled: '是否允许 Docker 沙箱后端。本机 docker.sock 等同宿主机 root，默认关闭。仅系统管理员可打开；打开后立即生效，无需重启。私有化单机且已挂载 daemon socket，或配置了带 TLS 的远程 tcp:// 时再启用。'
        },
        ssrf: {
          whitelist: 'SSRF 防护白名单。可填入 example.com / *.foo.com / 10.0.0.0/8 / 2001:db8::1。修改后立即生效。SSRF_WHITELIST_EXTRA 环境变量仍由部署方维护，不在此处覆盖。'
        },
        auth: {
          registration_mode: '注册模式。开放注册允许任何人创建账号；仅限邀请注册要求有效邀请链接；禁止注册不允许创建账号，但已有账号仍可接受邀请。保存后立即生效。',
          default_tenant_mode: '公开注册后的空间初始化策略。create_personal 会自动创建个人空间并授予 Owner；tenantless 仅创建账户，用户需要接受邀请或主动创建空间。只影响之后注册的用户。',
          complex_password_enabled: '是否启用复杂密码。开启后密码必须包含大小写字母、数字和特殊字符。修改后立即生效，只影响新注册用户或新密码修改/重置操作。特殊字符包含：{specialChars}'
        }
      },
      keyLabels: {
        model: {
          max_concurrency: '模型默认并发上限'
        },
        asynq: {
          core_concurrency: '核心解析保底并发数',
          postprocess_concurrency: '后处理编排并发数',
          enrichment_concurrency: '内容富化保底并发数',
          maintenance_concurrency: '维护与同步并发数',
          shared_concurrency: '共享弹性并发数',
          wiki_concurrency: 'Wiki Worker 并发数'
        },
        tenant: {
          max_owned_per_user: '每用户最大空间数',
          self_service_creation_enabled: '允许用户自助创建空间',
          default_storage_quota_gb: '新空间默认存储配额 (GB)',
          default_storage_quota_mb: '新空间默认存储配额 (MB)',
          auto_create_api_key: '创建空间时自动生成 API Key',
          auto_accept_invitation: '邀请已注册用户时自动加入'
        },
        sandbox: {
          docker_enabled: '启用 Docker 沙箱'
        },
        ssrf: {
          whitelist: 'SSRF 防护白名单'
        },
        auth: {
          registration_mode: '注册模式',
          default_tenant_mode: '注册默认空间策略',
          complex_password_enabled: '启用复杂密码'
        }
      },
      runtime: {
        queueDescriptions: {
          default: '文档解析、手工重解析',
          chat_attachment: '会话内上传附件解析',
          postprocess: '解析收尾、富化扇出',
          summary: '文档摘要、表格摘要',
          sync: '手动与定时同步',
          low: 'FAQ 导入、批量重解析、删除清理',
          multimodal: '图片 OCR、视觉描述',
          graph: '分块图谱抽取',
          question: '分块问题生成',
          wiki: '内容生成、索引收尾'
        },
        queueNames: {
          default: '文档解析',
          chat_attachment: '对话附件解析',
          postprocess: '后处理编排',
          summary: '摘要生成',
          sync: '数据源同步',
          low: '维护与批处理',
          multimodal: '多模态处理',
          graph: '图谱抽取',
          question: '问题生成',
          wiki: 'Wiki 处理'
        },
        poolDescriptions: {
          core: '文档解析与手工重解析的保底容量',
          postprocess: '解析完成后的收尾与富化扇出',
          enrichment: '摘要、图片、图谱与问题生成',
          maintenance: '数据源同步、批处理与删除清理',
          shared: '由核心解析与内容富化按积压借用',
          wiki: 'Wiki 内容生成与全局收尾'
        },
        pools: {
          core: '核心解析',
          postprocess: '后处理编排',
          enrichment: '内容富化',
          maintenance: '维护与同步',
          shared: '共享弹性',
          wiki: 'Wiki 池'
        },
        tasks: {
          taskTypes: {
            documentProcess: '文档解析',
            manualProcess: '手工重新处理',
            temporaryDocumentProcess: '聊天附件解析',
            postProcess: '文档后处理',
            summary: '摘要生成',
            tableSummary: '表格摘要生成',
            question: '问题生成',
            multimodal: '图片多模态处理',
            graph: '知识图谱抽取',
            sync: '数据源同步',
            faqImport: 'FAQ 导入',
            batchReparse: '批量重新解析',
            batchDelete: '批量删除',
            move: '文档移动',
            indexDelete: '索引删除',
            kbClone: '知识库复制',
            kbDelete: '知识库删除',
            wikiIngest: 'Wiki 内容生成',
            wikiFinalize: 'Wiki 收尾处理'
          }
        }
      }
    }
  },
  tenant: {
    title: '空间信息',
    currentTenant: '当前空间',
    switchTenant: '切换空间',
    statusActive: '活跃',
    statusInactive: '未激活',
    statusSuspended: '已暂停',
    statusUnknown: '未知',
    loadingInfo: '正在加载信息...',
    retry: '重试',
    unknown: '未知',
    formatError: '格式错误',
    searchPlaceholder: '搜索空间名称或输入空间 ID...',
    noMatch: '未找到匹配的空间',
    switchSuccessTitle: '已切换空间',
    switchSuccessContent: '你已进入 {name}',
    loadTenantsFailed: '加载空间列表失败',
    loading: '加载中...',
    api: {
      title: 'API 信息',
      userIdLabel: '用户 ID',
      userIdDescription: '您的唯一用户标识',
      usernameLabel: '用户名',
      usernameDescription: '您的登录用户名',
      createdAtLabel: '注册时间',
      createdAtDescription: '账户创建的时间'
    },
    messages: {
      fetchFailed: '获取空间信息失败',
      networkError: '网络错误，请稍后重试'
    },
    deleteDangerZone: {
      title: '删除当前空间',
      desc: '删除后，你将无法访问这个空间的个人文件、会话和智能体配置。账号和共享知识库会保留。',
      button: '删除空间',
      confirmTitle: '删除当前空间？',
      confirmBody: '确认删除空间「{name}」？此操作无法撤销。账号和共享知识库会保留。',
      confirmHint: '请输入空间名称「{name}」以确认删除。',
      confirm: '删除',
      nameMismatch: '空间名称不匹配',
      success: '空间已删除',
      failed: '删除空间失败'
    },
    leaveDangerZone: {
      title: '退出当前空间',
      desc: '终止您在本空间的成员身份。退出后将无法访问本空间的知识库与智能体，之后可被再次邀请加入。',
      button: '退出空间'
    },
    storage: {
      usageLabel: '存储使用率'
    },
    details: {
      idLabel: '空间 ID',
      nameLabel: '空间名称',
      descriptionLabel: '空间描述',
      businessLabel: '空间业务',
      statusLabel: '空间状态',
      createdAtLabel: '空间创建时间',
      editName: '修改名称',
      editNamePlaceholder: '请输入新的空间名称',
      editNameConfirm: '保存',
      editNameCancel: '取消',
      editNameRequired: '空间名称不能为空',
      editNameSuccess: '空间名称已更新',
      editNameFailed: '更新空间名称失败',
      editDescription: '修改描述',
      editDescriptionPlaceholder: '请输入新的空间描述',
      editDescriptionSuccess: '空间描述已更新',
      editDescriptionFailed: '更新空间描述失败',
      descriptionEmptyPlaceholder: '未填写'
    },
    create: {
      action: '创建新空间',
      dialogTitle: '创建新空间',
      dialogSubtitle: '个人文件保存在这个空间中，默认配额为 10 GB。所有账号共用 ContextDB 知识库。',
      nameLabel: '空间名称',
      namePlaceholder: '例如：我的新项目',
      nameRequired: '请输入空间名称',
      descriptionLabel: '描述（可选）',
      descriptionPlaceholder: '简单描述一下这个空间的用途',
      submit: '创建',
      cancel: '取消',
      success: '已创建空间',
      failed: '空间创建失败',
      disabled: '当前系统只允许通过邀请加入空间，不能自行创建空间。'
    },
    switcher: {
      menuLabel: '切换空间',
      currentBadge: '当前',
      homeTooltip: '我的空间',
      empty: '你目前只属于这一个空间'
    }
  },
  chat: {
    suggestedQuestions: '你可以这样问我',
    refreshSuggestedQuestions: '换一批',
    replaceDraftTitle: '替换草稿？',
    replaceDraftBody: '使用这条推荐问题替换输入框里的文字。',
    historyLoadFailed: '无法加载会话历史。',
    scrollToLatest: '跳到最新消息',
    thinking: '思考中...',
    thinkingAlt: '正在思考',
    preparingAnswer: '正在准备回答…',
    connectingModelAndGeneratingAnswer: '正在连接模型并生成回答…',
    modelStillResponding: '模型响应较慢，仍在等待…',
    deepThoughtCompleted: '已深度思考',
    deepThoughtAlt: '深度思考完成',
    referencesTitle: '参考了{count}个相关内容',
    referencesDocCount: '引用了{count}篇文档',
    referencesWebCount: '参考了{count}条网页',
    referencesDocAndWebCount: '引用了{docCount}篇文档和{webCount}条网页',
    referencesDrawerTitle: '参考来源',
    referencesDrawerTitleWeb: '网页来源',
    referencesDrawerTitleDocs: '文档来源',
    referencesDrawerTitleTools: '工具结果',
    referencesDrawerTitleMixed: '参考来源',
    referencesDrawerWebSection: '网页',
    referencesDrawerDocsSection: '知识库文档',
    referencesDrawerToolsSection: '工具',
    referencesDrawerEmpty: '暂无参考来源',
    questionMinimapTitle: '问答',
    questionMinimapPosition: '第 {current} 轮 · 共 {total} 轮',
    questionMinimapAriaLabel: '提问目录',
    questionMinimapAttachmentPlaceholder: '（附件）',
    referenceChunkCount: '{count}个片段',
    fallbackHint: '未从知识库中检索到相关内容，以上为模型直接回答',
    truncatedHint: '回答在模型单次输出上限处被截断，以上为截断前已生成的内容',
    requestInfoTitle: '请求信息',
    requestInfoRequestId: 'Request ID',
    requestInfoMessageId: '消息 ID',
    requestInfoSessionId: '会话 ID',
    requestInfoUrl: '请求',
    requestInfoSentAt: '发起时间',
    requestInfoEmpty: '暂无请求信息',
    channelWeb: '网页',
    channelApi: 'API',
    channelIm: 'IM',
    chunkLabel: '片段{index}:',
    navigateToDocument: '查看文档详情',
    referenceSourceBack: '全部引用',
    referenceSourceView: '查看原文',
    referenceSourceRelocate: '重新定位',
    referenceSourceLocating: '正在定位引用位置…',
    referenceSourceExact: '已精确定位原文片段',
    referenceSourcePartial: '已高亮核验通过的原文片段，部分引用内容尚未匹配',
    referenceSourceBlock: '已定位到来源区域，尚未精确匹配文字',
    referenceSourceAmbiguous: '原文有多处相同内容，无法唯一定位',
    referenceSourceStale: '原文或内容已更新，当前引用无法精确定位',
    referenceSourcePrevious: '上一处引用',
    referenceSourceNext: '下一处引用',
    referenceSourceFoundPage: '已定位到第 {page} 页',
    referenceSourceNotFound: '未能精确定位引用内容，已为你打开原文',
    referenceSourceOpenWeb: '打开原网页并定位',
    chunkIdLabel: '片段ID:',
    documentIdLabel: '文档ID:',
    faqIdLabel: 'FAQ ID:',
    faqContainerIdLabel: '所属文档ID:',
    faqAnswersLabel: '答案:',
    chunkOrdinal: '片段 {index}',
    previewContent: '预览内容',
    noPlanSteps: '未提供具体步骤',
    chunkIndexLabel: '片段 #{index}',
    chunkPositionLabel: '(位置: {position})',
    noRelatedChunks: '没有找到相关片段',
    noSearchResults: '没有找到搜索结果',
    relevanceHigh: '高相关',
    relevanceMedium: '中相关',
    relevanceLow: '低相关',
    relevanceWeak: '弱相关',
    webSearchNoResults: '未找到搜索结果',
    otherSource: '其他来源',
    webGroupIntro: '以下 {count} 条内容来自',
    graphConfigTitle: '图谱配置',
    entityTypesLabel: '实体类型:',
    relationTypesLabel: '关系类型:',
    graphResultsHeader: '找到 {count} 条相关结果',
    graphNoResults: '未找到相关的图谱信息',
    unknownLink: '未知链接',
    contentLengthLabel: '长度 {value}',
    notProvided: '未提供',
    errorMessageLabel: '错误信息',
    summaryLabel: '总结',
    rawTextLabel: '原始文本',
    collapseRaw: '收起原文',
    expandRaw: '展开原文',
    noWebContent: '未获取到网页内容',
    webFetchStatusSuccess: '抓取成功',
    webFetchStatusFailed: '抓取失败',
    webFetchStatusSkipped: '已跳过',
    webFetchErrorCode: '错误码',
    webFetchRetryable: '可重试',
    webFetchContentRange: '字符范围 {start}–{end}，共 {total} 字符',
    webFetchPartialContent: '部分页面内容',
    webFetchSummaryFailed: '摘要失败',
    lengthChars: '{value} 字',
    lengthThousands: '{value} 千字',
    lengthTenThousands: '{value} 万字',
    noDatabaseRecords: '未找到匹配的记录',
    nullValuePlaceholder: '<NULL>',
    chunkCountValue: '{count} 个片段',
    documentDescriptionLabel: '文档描述:',
    documentSourceLabel: '来源:',
    documentFileLabel: '文件信息:',
    documentMetadataLabel: '元数据',
    documentInfoEmpty: '暂无文档信息',
    positionLabel: '位置:',
    chunkPositionValue: '第 {index} 个片段',
    contentLengthLabelSimple: '内容长度:',
    fullContentLabel: '完整内容',
    copyContent: '复制内容',
    knowledgeBaseCount: '共 {count} 个知识库',
    noKnowledgeBases: '没有可用的知识库',
    rawOutputLabel: '原始输出',
    wikiWritePageTitle: 'Wiki 页面写入',
    wikiReplaceTextTitle: 'Wiki 文本替换',
    wikiRenamePageTitle: 'Wiki 页面重命名',
    wikiDeletePageTitle: 'Wiki 页面删除',
    wikiActionCreated: '已创建',
    wikiActionUpdated: '已更新',
    wikiActionRenamed: '已重命名',
    wikiActionDeleted: '已删除',
    wikiFieldSlug: '页面路径',
    wikiFieldTitle: '标题',
    wikiFieldPageType: '类型',
    wikiFieldSummary: '摘要',
    wikiFieldOldText: '原文本',
    wikiFieldNewText: '新文本',
    wikiFieldOldSlug: '原路径',
    wikiFieldNewSlug: '新路径',
    wikiFieldAffectedPages: '受影响页面',
    wikiAffectedCount: '{count} 个页面的链接已更新',
    processError: '处理出错',
    sessionExcerpt: '会话摘录',
    noAnswerContent: '（无回答内容）',
    manualSourcesHeading: '参考来源',
    noMatchFound: '未找到匹配的内容',
    deleteSessionFailed: '删除失败，请稍后再试！',
    imageTooMany: '最多上传5张图片',
    imageTypeSizeError: '仅支持 JPG/PNG/GIF/WEBP 格式，单张不超过 10MB',
    imageUploadTooltip: '上传图片（支持粘贴/拖拽）',
    attachmentUploadTooltip: '上传附件（文档、音频等）',
    attachmentWithCount: '已上传 {count} 个附件',
    attachmentTooMany: '最多上传 {max} 个附件',
    attachmentTotalTooMany: '图片和附件合计最多 {max} 个',
    attachmentTooLarge: '文件 {name} 超过 {max}MB 限制',
    attachmentTypeNotSupported: '不支持的文件类型：{name}',
    attachmentUploading: '上传中 {progress}%',
    attachmentParsing: '正在解析',
    attachmentReady: '解析完成',
    attachmentUploadFailed: '附件上传失败',
    attachmentParseFailed: '附件解析失败',
    attachmentStillProcessing: '附件 {name} 仍在解析，请稍候',
    memoryUsedCount: '本次使用了 {count} 条记忆',
    memoryForget: '删除这条记忆',
    memoryForgotten: '已删除这条记忆',
    memoryForgetFailed: '删除失败',
    memoryHint: '这些是助手在回答时看到的长期记忆，删除后不会再被使用。',
    backgroundWork: {
      count: '{count} 个后台任务',
      refresh: '刷新',
      structuredResult: '结构化结果',
      updateMessage: '追加任务说明',
      sendUpdate: '发送更新',
      stopRequested: '已请求取消',
      actionFailed: '操作失败，请重试',
      cancelFailed: '取消失败，请重试',
      stop: '停止',
      loading: '正在加载输出…',
      unavailable: '暂时无法查看输出',
      states: {
        pending: '排队中',
        running: '运行中',
        waiting: '等待响应',
        succeeded: '已完成',
        failed: '失败',
        cancelled: '已取消',
        lost: '状态不可用'
      }
    },
    rewind: {
      tooltip: '回滚到这里',
      confirmTitle: '回滚到这里？',
      confirmBody: '此条之后的对话将被删除；从提问回滚时，该问题会填回输入框。有检查点时工作区也会一并回退，操作不可撤销。',
      confirmButton: '回滚',
      cancelButton: '取消',
      success: '已回滚',
      reloadFailed: '对话已回滚，但未能重新加载历史。若较早消息缺失，请刷新页面',
      failed: '回滚失败，请重试',
      skipped: '对话已回滚，工作区未改动',
      skipNoSandbox: '对话已回滚，工作区未改动（当前没有沙箱）',
      skipNoCheckpoint: '对话已回滚，工作区未改动（没有可回退的检查点）'
    },
    sandbox: {
      panelTitle: '沙箱可视化',
      tabArtifacts: '产物',
      tabTerminal: '终端',
      tabDesktop: '桌面',
      artifactsEmpty: '本会话尚未生成可下载的文件',
      artifactScope: '产物范围',
      artifactsCurrent: '本轮',
      artifactsAll: '全部',
      artifactsSearch: '搜索文件名',
      artifactsNoMatches: '没有匹配的文件',
      desktopNotStarted: '桌面尚未连接。连接后会接入本会话的沙箱环境。',
      desktopStart: '连接桌面',
      desktopStarting: '正在连接桌面…（首次约需 3–8 秒）',
      desktopUnsupported: '当前沙箱配置不支持桌面。需要在工作区沙箱设置的模板列表里选中带桌面的镜像，且后端为 Cube 或 E2B。',
      desktopBusy: '本会话已有一个桌面连接。桌面同一时刻只允许一个连接，否则会出现两个人抢同一套键鼠。',
      desktopStartFailed: '桌面启动失败，可以重试。',
      desktopRebuilt: '沙箱已因技能更新重建，原桌面及未保存的内容已丢失。重新连接会得到一个全新桌面。',
      desktopNeedsProvision: '本会话当前没有运行中的沙箱环境。创建并连接会新建一个沙箱，并按工作区配置计费。',
      desktopCreateAndStart: '创建并连接',
      desktopPaused: '本会话的沙箱已暂停。连接桌面会唤醒它。',
      desktopDisconnected: '桌面连接已断开',
      desktopIdleDisconnected: '桌面空闲已断开，沙箱将按工作区 TTL 自行暂停。可重新连接。',
      desktopRetry: '重新连接',
      paused: '本会话的沙箱已暂停。启动终端会唤醒它。',
      stopped: '本会话的沙箱未在运行：可能已停止，或因长时间空闲已被回收。启动终端会重新启动它；若已被回收，则会新建一个沙箱，之前的文件和安装的软件不会保留。',
      start: '启动终端',
      connecting: '正在连接沙箱…',
      needsProvision: '本会话当前没有运行中的沙箱环境。创建并启动会新建一个沙箱，并按工作区配置计费。',
      createAndStart: '创建并启动',
      noSandbox: '会话尚未创建沙箱，且当前智能体未配置沙箱后端，无法确定在哪个后端创建。请切换到配置了沙箱的智能体，或发送一条需要执行代码的消息。',
      unsupported: '当前沙箱后端不支持交互终端',
      disconnected: '连接已断开',
      retry: '重新连接',
      sessionEnded: '终端会话已结束',
      idleDisconnected: '终端空闲已断开，沙箱将按工作区 TTL 自行暂停。可重新连接。',
      idleDisconnectedNewShell: '终端空闲已断开，其中的 shell 已结束（nohup 启动的后台任务不受影响）。重新连接会打开一个新的 shell。',
      disconnectedNewShell: '连接已断开，终端中的 shell 已结束（nohup 启动的后台任务不受影响）。重新连接会打开一个新的 shell。',
      authRevoked: '登录状态已失效，终端已断开。请重新登录后再连接。'
    },
    conversationTime: {
      today: '今天 {time}',
      yesterday: '昨天 {time}',
      thisYear: '{month}月{day}日 {time}',
      otherYear: '{year}年{month}月{day}日 {time}'
    }
  },
  knowledgeEditor: {
    titleCreate: '新建知识库',
    titleEdit: '知识库设置',
    advanced: {
      title: '高级设置',
      description: '配置问题生成等高级功能',
      multimodal: {
        label: '多模态功能',
        description: '启用图片等多模态内容的理解能力',
        vllmLabel: 'VLLM 视觉模型',
        vllmDescription: '用于多模态理解的视觉语言模型（必选）',
        vllmPlaceholder: '请选择 VLLM 模型（必选）',
        descriptionLanguageLabel: '图片描述语言',
        descriptionLanguageDescription: '留空时跟随文档语言；不再强制使用中文',
        descriptionLanguageAuto: '自动跟随文档语言',
        customInstructionsLabel: '图片解析要求',
        customInstructionsDescription: '补充需要重点识别的视觉信息，OCR 和 Markdown 格式协议保持不变',
        customInstructionsPlaceholder: '例如：重点识别设备铭牌、型号、告警代码和表格中的单位…',
        imageVectorLabel: '图片向量检索',
        imageVectorDescription: '开启后，生成图片描述之后再用向量模型直接对图片编码，检索时按图片内容召回描述没写到的信息。需要向量模型支持图片输入；每张图片多一次向量调用，向量检索的候选范围也会放大。只对此后入库或重新解析的文档生效，扫描件 PDF 页不生成',
        imageVectorModelUnsupported: '当前向量模型未声明图片输入，开启后不会生成或召回图片向量',
        imageAttrsSchemaLabel: '可观察的图片属性',
        imageAttrsSchemaDescription: '模型会观察以下属性（由后端注册表定义）以驱动 OCR 策略',
        imagePipelineSectionLabel: '图片解析方案',
        imagePipelineSectionDescription: '多模态解析开启后，可以根据需要选择图片的解析方案',
        imagePipelineLabel: '选择解析方案',
        advancedSettingsLabel: '高级设置',
        notesLabel: '附加说明',
        imagePipelinePlaceholder: '请选择解析方案',
        imagePipelineLoading: '正在读取流水线…',
        imagePipelineLoadError: '读取流水线失败',
        imagePipelineValidateError: '无法校验当前设置，保存时后端会再次检查。',
        imageAttrsOcrConditions: '根据观察到的属性条件触发 OCR',
        imageAttrsOcrConditionsDesc: '当观察到的属性满足以下条件时，对图片进行 OCR',
        imagePipelineKbNote: '默认跟随知识库设置，可针对本次任务调整'
      },
      tableMetadataInstructions: {
        label: '表格元数据生成要求',
        description: '为 CSV/Excel 摘要补充业务背景和字段语义，帮助后续检索理解表格内容',
        placeholder: '例如：这是销售订单表，金额单位为元，status 字段使用公司内部状态码…'
      },
      autoTag: {
        label: '自动关联标签',
        description: '文档解析完成后，从当前知识库已有标签中选择合适标签自动关联。不会创建或删除标签，并会增加一次模型调用。',
        modelLabel: '分类模型',
        modelDescription: '留空时使用知识库摘要模型。',
        modelPlaceholder: '请选择分类模型',
        maxTagsLabel: '单篇文档最多标签数',
        maxTagsDescription: '每篇文档最多自动关联 1-10 个已有标签。',
        skipIfTaggedLabel: '跳过已有标签的文档',
        skipIfTaggedDescription: '开启后，上传时已手动设置标签的文档不再自动打标签，避免覆盖人工分类意图。'
      },
      profile: {
        label: '自动生成知识库描述',
        description: '文档新增、删除或摘要更新后，从文档画像聚合自动生成知识库描述。聚合本身不调用模型，仅当聚合结果变化时才发起一次小模型调用。',
        modelLabel: '生成模型',
        modelDescription: '留空时使用知识库摘要模型。',
        modelPlaceholder: '请选择生成模型',
        instructionsLabel: '描述生成要求',
        instructionsDescription: '补充面向的读者、需要保留的术语或表达风格，系统仍维护稳定的输出格式。',
        instructionsPlaceholder: '例如：面向售后客服，用通俗说法描述产品线，保留产品型号…'
      },
      questionGeneration: {
        modelLabel: '问题生成模型',
        modelDescription: '留空时使用知识库摘要模型。',
        modelPlaceholder: '请选择问题生成模型',
        label: 'AI 问题生成',
        description: '解析文档时调用大模型为每个分块生成相关问题，提高检索召回率。启用后会增加文档解析耗时。',
        countLabel: '生成问题数量',
        countDescription: '每个文档分块生成的问题数量（1-10）',
        instructionsLabel: '问题生成要求',
        instructionsDescription: '指定问题面向的人群、场景和表达方式，系统仍维护稳定输出格式',
        instructionsPlaceholder: '例如：生成客服用户常问的自然语言问题，避免考试题式表达…'
      }
    },
    asr: {
      title: '音频语音识别',
      description: '配置语音识别（ASR），启用后可上传音频文件并整段转写为文本（常见格式：mp3、wav、m4a、flac、ogg 等）。暂不支持视频上传。',
      label: '启用音频语音识别',
      desc: '启用后可上传音频到知识库，系统自动将语音转写为文本并参与解析与检索',
      modelLabel: 'ASR 模型',
      modelDescription: '用于音频中语音转文本的识别模型（如 OpenAI Whisper）',
      modelPlaceholder: '请选择 ASR 模型',
      languageLabel: '音频语言提示',
      languageDescription: '可选；指定主要语种可提高部分 ASR 模型的识别稳定性，留空时自动检测',
      languagePlaceholder: '例如 zh、en，留空自动检测'
    },
    multimodal: {
      title: '图像处理配置',
      description: '配置图像内容理解能力，启用后支持图片等非文本内容的解析和检索'
    },
    chunking: {
      title: '分块设置',
      description: '控制上传文档在嵌入前的切分方式。默认值适用于大多数场景，仅在检索质量异常时调整。',
      sizeLabel: '分块大小',
      sizeDescription: '每个分块的最大字符数（100-4000）。默认 512 ≈ 中文 300 tokens / 英文 100-130 tokens。FAQ 用 200-400，叙述性长文档用 1000-2000。',
      characters: '字符',
      overlapLabel: '分块重叠',
      overlapDescription: '相邻分块之间共享的字符数（0-500）。默认 80 ≈ 分块大小的 15%，符合当前研究推荐。FAQ/结构化数据用 0，长篇叙述用 150-200。',
      separatorsLabel: '分隔符',
      separatorsDescription: '切分时优先使用的字符或字符串。优先级高的分隔符先尝试；默认顺序优先段落 → 句子 → 标点。',
      separatorsPlaceholder: '选择或自定义分隔符',
      parentChildLabel: '父子分块',
      parentChildDescription: '两级分块：小的子块用于向量匹配（精准命中），大的父块返回给 LLM（更丰富上下文）。建议用于长文档（>10 页）；短 FAQ 可关闭以节省存储。',
      parentChunkSizeLabel: '父块大小',
      parentChunkSizeDescription: '返回给 LLM 的上下文块大小（512-8192）。默认 4096 ≈ 1000 英文 tokens，适合所有现代 LLM 上下文窗口。',
      childChunkSizeLabel: '子块大小',
      childChunkSizeDescription: '用于向量匹配的嵌入块大小（64-2048）。默认 384 ≈ 80 tokens，是 sentence-transformer / BGE 类嵌入模型的最佳点。',
      strategyLabel: '分块策略',
      strategyDescription: '选择文档的分块方式。自动模式会分析每个文档的结构并选择最佳策略。',
      strategyPlaceholder: '选择分块策略（不填则按长度切分）',
      overlapWarning: '重叠相对于分块大小较大——分块之间会共享大部分内容。',
      advancedLabel: '高级选项',
      tokenLimitLabel: '每块 Token 上限',
      tokenLimitDescription: '每个分块的硬性 Token 上限（0-8192）。0 = 关闭（仅按字符数）。当嵌入模型 Token 上限较小时启用：MiniLM (256 tok) 用 200，BGE/Cohere (512 tok) 用 400。现代嵌入器（OpenAI、Voyage、Jina-v3）支持 >2000 tokens，保持 0 即可。',
      languagesLabel: '语言提示',
      languagesDescription: '限制启发式模式只识别选定的语言（DE/EN/ZH）。留空 = 自动检测。同质化语料库可显式设置以避免跨语言误匹配。',
      languagesPlaceholder: '自动检测',
      debug: {
        toggle: '测试分块效果',
        toggleHint: '无需重新上传即可对示例文本运行分块器',
        sampleLabel: '示例文本',
        samplePlaceholder: '粘贴 Markdown / 纯文本片段以查看当前配置的分块结果…',
        presetLabel: '载入示例：',
        runButton: '运行预览',
        loading: '正在对示例运行分块器…',
        errorPrefix: '预览失败',
        selectedTier: '选定策略',
        rejected: '被拒绝的层级',
        contextHeader: '上下文标题',
        fallbackWarning: '策略链已穷尽 — 当前设置无法智能分块此内容',
        stats: {
          chunks: '块',
          truncated: '已截断；总数 {total}'
        },
        profile: {
          lines: '行',
          chars: '字符',
          headings: 'Markdown 标题',
          pageBreaks: '分页符',
          chapterMarkers: '章节标记',
          languages: '语言'
        },
        samples: {
          markdown: 'Markdown 文档',
          faq: 'FAQ 列表',
          chapter: 'PDF 章节',
          plain: '纯文本'
        }
      },
      languageOptions: {
        de: '德语',
        en: '英语',
        zh: '中文'
      },
      strategies: {
        legacy: {
          label: '按长度切分',
          tooltip: '忽略结构，仅按字符数和分隔符递归切分——原始行为。当上述策略对你的内容效果不佳时使用。'
        },
        heuristic: {
          label: '结构感知',
          tooltip: '识别分页符、编号章节、多语言章节标记（DE/EN/ZH）、全大写标题等结构信号进行切分。适合没有 Markdown 标题的 PDF / 扫描件。'
        },
        heading: {
          label: '按标题切分',
          tooltip: '在 Markdown 标题（#、##、###）边界处切分，每块自动带上所在标题路径。适合结构清晰的 Markdown 文档。'
        },
        auto: {
          label: '自动',
          tooltip: '文档分析器根据内容结构自动在「按标题切分」「结构感知」「按长度切分」之间选择。'
        }
      },
      separators: {
        doubleNewline: '双换行 (\\n\\n)',
        singleNewline: '单换行 (\\n)',
        periodCn: '中文句号 (。)',
        exclamationCn: '感叹号 (！)',
        questionCn: '问号 (？)',
        semicolonCn: '中文分号 (；)',
        semicolonEn: '英文分号 (;)',
        space: '空格 ( )'
      }
    },
    models: {
      title: '模型配置',
      description: '为知识库选择合适的 AI 模型',
      llmLabel: 'LLM 大语言模型',
      llmDesc: '用于总结和摘要的大语言模型',
      llmPlaceholder: '请选择 LLM 模型（可选）',
      embeddingLabel: 'Embedding 嵌入模型',
      embeddingDesc: '用于文本向量化的嵌入模型',
      embeddingPlaceholder: '请选择 Embedding 模型',
      embeddingLocked: '知识库中已有文件，无法修改 Embedding 模型',
      embeddingOptional: '（可选）',
      embeddingWikiOptionalDesc: '可选。配置后用于 Wiki 目录归类的相似度匹配，让新页面更好地复用已有目录；不配置则按完整目录树归类。'
    },
    faqImport: {
      title: '批量导入 FAQ'
    },
    faq: {
      title: '问答',
      description: '设置 FAQ 知识库的索引策略和问答组织方式',
      indexModeLabel: '索引方式',
      indexModeDescription: '仅索引问题可提升精度，索引问答可提高召回率',
      questionIndexModeLabel: '问题索引方式',
      questionIndexModeDescription: '合并索引：标准问和相似问合并索引；分别索引：标准问和每个相似问独立索引，检索更精确但需要更多存储',
      entryGuide: 'FAQ 条目由标准问、相似问、反例和多个答案组成，可在知识库详情中批量导入、编辑。',
      modes: {
        questionOnly: '仅标准问/相似问',
        questionAnswer: '标准问 + 答案',
        combined: '合并索引',
        separate: '分别索引'
      }
    },
    document: {
      title: '文档'
    },
    messages: {
      loadModelsFailed: '加载模型列表失败',
      loadDataFailed: '加载知识库数据失败',
      notFound: '知识库不存在',
      nameRequired: '请输入知识库名称',
      summaryRequired: '请选择 Summary 模型',
      multimodalInvalid: '多模态配置验证失败',
      createSuccess: '已创建知识库',
      createFailed: '创建知识库失败',
      missingId: '缺少知识库 ID',
      buildDataFailed: '数据构建失败',
      updateSuccess: '配置已保存',
      indexModeRequired: '请选择 FAQ 的索引方式',
      storageChangeConfirm: '知识库中已有文件，更改存储引擎后旧文件可能无法正常访问。是否确认更改？'
    },
    share: {
      description: '将知识库共享给空间，让空间成员可以访问和使用',
      hintTitle: '共享说明',
      addShare: '共享',
      unshareConfirm: '确定要取消对「{name}」的共享吗？',
      tip1: '共享后，空间成员将根据设定的权限访问此知识库',
      tip2: '可编辑权限允许成员修改知识库内容，只读权限仅允许检索和问答'
    },
    postCreateHint: {
      title: '创建成功',
      footer: '可继续调整配置，设置共享与数据源，完成后点击「保存并关闭」。',
      followUpDesc: '可在左侧配置数据源，或在「共享管理」中发布到空间'
    },
    footer: {
      instantEffect: '此页的更改即时生效，无需保存'
    },
    buttons: {
      create: '创建知识库',
      saveAndClose: '保存并关闭'
    },
    wikiBrowser: {
      viewInGraph: '在图谱中查看',
      filterSummary: '摘要',
      filterEntity: '实体',
      filterConcept: '概念',
      filterSynthesis: '综合',
      filterComparison: '对比',
      version: 'v{ver}',
      gallery: {
        attr: {
          builtin_caption: '描述',
          builtin_caption_description: '模型生成的图片描述',
          builtin_ocr_text: 'OCR 文本',
          builtin_ocr_text_description: 'OCR 从图片中提取的文字',
          builtin_page: '文档页码',
          builtin_page_description: '按来源文档分组，再按 PDF 页码排序；未知页码放在文档末尾。',
          builtin_created_at: '创建时间',
          builtin_created_at_description: '所属文档片段的创建时间',
          builtin_updated_at: '更新时间',
          builtin_updated_at_description: '所属文档片段的最后更新时间',
          builtin_is_enabled: '启用状态',
          builtin_is_enabled_description: '所属文档片段是否参与检索',
          builtin_is_enabled_value_true: '已启用',
          builtin_is_enabled_value_false: '已停用'
        }
      }
    },
    indexing: {
      title: '索引策略',
      description: '配置文档上传后的处理管道，可以独立开启或关闭每种索引方式',
      searchTitle: 'RAG 检索',
      searchDesc: '对文档进行分块、向量化和关键词索引，支持混合检索',
      wikiTitle: 'Wiki 知识库',
      wikiDesc: '自动生成互相关联的 Wiki 知识页面，构建结构化知识体系',
      atLeastOne: '至少需要开启一种索引策略',
      embeddingRequired: 'RAG 检索需要配置 Embedding 模型',
      lockedTip: '知识库已有内容，索引策略暂不支持调整。如需变更，请先清空知识库。',
      rebuildConfirmTitle: '重建索引',
      rebuildConfirmBody: '索引策略已变更，是否对已有的 {count} 篇文档重新处理？这可能需要一些时间。',
      rebuildSuccess: '已提交重建任务，共 {count} 篇文档',
      rebuildSkip: '稍后可在数据源中手动触发重建'
    },
    wiki: {
      title: 'Wiki 设置',
      synthesisModelLabel: 'Wiki 合成模型',
      synthesisModelPlaceholder: '选择用于 Wiki 生成的 LLM 模型',
      synthesisModelTip: '不设置时将回退使用摘要模型',
      autoGenerateLabel: '自动生成 Wiki 页面',
      autoGenerateTip: '关闭后仍可浏览和手工维护 Wiki 页面，但文档处理不会自动调用 LLM 生成或更新页面',
      extractionGranularityLabel: '提取粒度',
      contentInstructionsLabel: 'Wiki 内容生成要求',
      contentInstructionsTip: '控制摘要、页面和首页的表达重点；引用、合并与防幻觉规则由系统固定维护。修改后需重新解析才能影响已有内容。',
      contentInstructionsPlaceholder: '例如：使用法务审阅口吻，优先展示责任主体、时间线和风险提示…',
      extractionInstructionsLabel: 'Wiki 提取重点',
      extractionInstructionsTip: '说明应重点识别的领域实体和概念，不会替换系统的 JSON 与引用协议。',
      extractionInstructionsPlaceholder: '例如：重点识别产品、版本、组织、负责人和关键技术概念…',
      extractionGranularityTip: '控制每篇文档抽取的 Wiki 实体/概念数量。粒度越细，索引越聚焦；粒度越粗，索引越详尽',
      granularityFocused: '聚焦',
      granularityStandard: '标准',
      granularityExhaustive: '详尽',
      granularityFocusedHint: '只抽取文档的主角（如简历 → 人物和项目）。最干净，但可能漏掉次要实体。',
      granularityStandardHint: '抽取主角 + 被详细描述的次要实体/概念。跳过一带而过的通用名词。适合大多数场景。',
      granularityExhaustiveHint: '抽取所有可识别的命名实体与概念，包括一带而过的技术栈。适合将知识库当作术语表使用。'
    },
    basic: {
      title: '基本信息',
      description: '设置知识库的名称和描述信息',
      kbId: '知识库 ID',
      kbIdDesc: 'API 集成时可使用此 ID 指定知识库',
      typeLabel: '知识库类型',
      typeDocument: '文档',
      typeFAQ: '问答',
      typeDescription: 'FAQ 类型适合结构化问答数据；文档型支持文件解析与分块；Wiki 类型由 LLM 自动构建互链知识页面。',
      nameLabel: '知识库名称',
      namePlaceholder: '请输入知识库名称',
      descriptionLabel: '知识库描述',
      descriptionPlaceholder: '请输入知识库描述（可选）',
      profile: {
        title: 'AI 生成描述',
        hint: '由文档画像聚合生成，不会覆盖上方手写描述；智能体会同时读取两者来判断问题是否该在本知识库中检索。',
        empty: '尚未生成。上传文档并生成摘要后，点击下方按钮即可生成。',
        noDocuments: '知识库中还没有已解析完成的文档。',
        questions: '典型问题',
        generate: '生成 AI 描述',
        regenerate: '重新生成',
        adopt: '用作知识库描述',
        generated: 'AI 描述已生成',
        generateFailed: 'AI 描述生成失败',
        adopted: '已填入知识库描述，保存后生效',
        failed: '上次生成失败：{error}',
        generatedAt: '生成于 {time} · 基于 {count} 篇文档'
      }
    },
    errors: {
      vectorStoreBindingInvalid: '无法使用所选向量存储。请选择其他存储或使用系统默认值。',
      vectorStoreUnavailable: '所选向量存储当前不可用。请在设置 → 向量存储中检查其连接配置。'
    },
    sidebar: {
      basic: '基本信息',
      models: '模型配置',
      vectorStore: '向量存储',
      chunking: '分块设置',
      storage: '存储引擎',
      advanced: '高级设置',
      faq: 'FAQ 设置',
      graph: '知识图谱',
      multimodal: '图像处理',
      asr: '音频处理',
      datasource: '数据源',
      share: '共享管理',
      activity: '活动记录'
    },
    navGroups: {
      basic: '基础',
      processing: '索引与解析',
      data: '存储与数据',
      integration: '发布集成',
      management: '管理与审计'
    },
    activity: {
      title: '活动记录',
      description: '查看这个知识库的重要变更与后台任务入口，记录默认遵循审计日志保留策略。',
      allOutcomes: '全部结果',
      allActions: '全部操作',
      refresh: '刷新',
      retry: '重试',
      empty: '暂无活动记录',
      emptyFiltered: '没有匹配的活动记录',
      clearFilters: '清除筛选',
      loadingMore: '加载中…',
      end: '没有更早的记录了',
      loadFailed: '活动记录加载失败',
      systemActor: '系统触发',
      actorWithAPIKey: '{actor} · API Key · {name}',
      actorAPIKey: 'API Key · {name}',
      viaAssistant: '经小知助手',
      knowledgeBase: '知识库',
      countItems: '共 {count} 项',
      titleWithCount: '{title} 等 {count} 项',
      importSummary: '成功 {success} / 失败 {failed} / 跳过 {skipped}',
      detailValues: {
        user: '用户发起',
        manual: '手动触发',
        schedule: '定时调度',
        system: '系统触发',
        pending: '待处理',
        completed: '已完成',
        partial: '部分完成',
        canceled: '已取消',
        failed: '失败',
        enqueue: '任务提交',
        reuse_vectors: '复用向量',
        reparse: '重新解析',
        viewer: '只读',
        editor: '可编辑',
        admin: '管理',
        append: '追加',
        replace: '覆盖'
      },
      outcomes: {
        accepted: '已受理',
        success: '成功',
        failed: '失败',
        partial: '部分完成',
        canceled: '已取消',
        denied: '已拒绝'
      },
      actions: {
        'kb.created': '创建知识库',
        'kb.updated': '更新知识库',
        'kb.deleted': '删除知识库',
        'kb.duplicated': '复制知识库',
        'kb.clone_started': '开始克隆',
        'kb.clone_completed': '完成克隆',
        'kb.clone_failed': '克隆失败',
        'knowledge.created': '添加知识',
        'knowledge.updated': '更新知识',
        'knowledge.deleted': '删除知识',
        'knowledge.batch_deleted': '批量删除知识',
        'knowledge.reparse_started': '开始重新解析',
        'knowledge.parse_canceled': '取消解析',
        'knowledge.move_started': '开始移动知识',
        'knowledge.move_completed': '完成移动知识',
        'knowledge.move_failed': '移动知识失败',
        'tag.created': '创建标签',
        'tag.updated': '更新标签',
        'tag.deleted': '删除标签',
        'datasource.created': '创建数据源',
        'datasource.updated': '更新数据源',
        'datasource.deleted': '删除数据源',
        'datasource.sync_started': '开始同步数据源',
        'datasource.sync_completed': '数据源同步完成',
        'datasource.sync_failed': '数据源同步失败',
        'datasource.paused': '暂停数据源',
        'datasource.resumed': '恢复数据源',
        'kb.share_added': '添加共享',
        'kb.share_permission_changed': '修改共享权限',
        'kb.share_removed': '移除共享',
        'wiki.content_changed': '更新 Wiki 内容',
        'faq.import_started': '开始导入 FAQ',
        'faq.import_completed': '完成导入 FAQ',
        'faq.import_failed': '导入 FAQ 失败'
      },
      detailFields: {
        task_id: '任务 ID',
        trigger: '触发方式',
        processing_status: '处理状态',
        source_kb_id: '来源知识库 ID',
        target_kb_id: '目标知识库 ID',
        sync_log_id: '同步记录 ID',
        mode: '执行模式',
        attempt: '处理批次',
        count: '项目数',
        total: '总数',
        processed: '已处理',
        failed: '失败数',
        skipped: '跳过数',
        failure_stage: '失败阶段'
      },
      targets: {
        knowledge_base: '知识库',
        knowledge: '知识',
        faq_entry: 'FAQ 条目',
        knowledge_tag: '标签',
        data_source: '数据源',
        knowledge_base_share: '共享',
        knowledge_move: '知识移动',
        wiki: 'Wiki'
      },
      drawer: {
        sectionSummary: '摘要',
        sectionIdentifiers: '标识符',
        sectionTask: '任务信息',
        targetChange: '变更详情'
      },
      expanded: {
        targetType: '对象类型',
        targetId: '对象 ID',
        actorId: '发起人 ID',
        apiKeyName: 'API Key 名称',
        apiKeyId: 'API Key ID',
        agentSessionId: '助手会话 ID',
        agentOperation: '助手操作',
        details: '详情'
      },
      columns: {
        time: '时间',
        action: '操作',
        target: '对象',
        actor: '发起人',
        outcome: '结果'
      }
    }
  },
  embedPublish: {
    copyCode: '复制代码'
  },
  knowledgeList: {
    detail: {
      title: '共享知识库',
      sourceOrg: '来源空间',
      myPermission: '我的权限'
    },
    sections: {
      tenantOthers: '本空间 · 其他成员',
      tenantReadonly: '本空间 · 仅查看'
    },
    empty: {
      title: '暂无知识库'
    }
  },
  createChat: {
    title: 'Hi，我是小知，让你的知识触手可及',
    newSessionTitle: '新会话',
    openProject: '选择项目',
    clearProject: '取消绑定',
    pickFailed: '无法打开所选路径',
    messages: {
      createFailed: '创建会话失败',
      createError: '创建会话失败，请稍后重试'
    }
  },
  input: {
    addModel: '添加模型',
    placeholder: '输入问题或描述任务…',
    agentMode: '智能推理',
    normalMode: '快速问答',
    normalModeDesc: '基于知识库的 RAG 问答',
    agentModeDesc: '多步思考，深度分析',
    agentMissingAllowedTools: '允许的工具',
    agentMissingSummaryModel: '对话模型',
    agentMissingRerankModel: '重排模型',
    customAgentMissingSummaryModel: '对话模型',
    customAgentMissingRerankModel: '重排模型',
    goToAgentEditor: '前往配置 →',
    agentNotReadyDetail: '智能体「{agentName}」未就绪，需要配置以下内容：{reasons}',
    sharedAgentNotReadyDetail: '共享智能体「{agentName}」尚未就绪（缺少：{reasons}），请联系分享方管理员完成配置。',
    knowledgeBase: '知识库',
    knowledgeBaseWithCount: '知识库({count})',
    notConfigured: '未配置',
    sharedAgentModelLabel: '共享智能体配置的模型',
    noModel: '暂无可用模型',
    modelAuto: '默认',
    modelFollowDefault: '跟随默认',
    modelAutoHint: '当前知识库配置的对话模型；不在知识库页面或知识库未配置时，使用第一个可用的对话模型',
    stopGeneration: '停止生成',
    send: '发送',
    steerRetry: '重试发送',
    webSearchDisabledByAgent: '当前智能体已禁用网络搜索',
    kbLockedByAgent: '当前智能体已锁定知识库配置',
    kbDisabledByAgent: '当前智能体已禁用知识库功能',
    modelLockedByAgent: '当前智能体已锁定模型配置',
    imageUploadDisabledByAgent: '当前智能体未启用图片上传',
    voiceTooltip: '按住说话（{shortcut}）',
    voicePreparing: '麦克风准备中，按钮变红后再说话',
    voiceRecording: '正在录音，松开结束',
    voiceReleasedEarly: '麦克风还没准备好，请按住直到按钮变红再说话',
    voiceTranscribing: '正在识别语音…',
    voiceUnsupported: '当前浏览器不支持录音',
    voiceInsecureContext: '语音输入需要 HTTPS 或 localhost 访问',
    voicePermissionDenied: '无法使用麦克风，请在浏览器中允许麦克风权限',
    voiceDeviceError: '未找到可用的麦克风',
    voiceDecodeError: '录音处理失败，请重试',
    voiceTranscribeFailed: '语音识别失败，请检查智能体的 ASR 模型配置',
    voiceEmptyResult: '未识别到语音内容',
    goToAgentSettings: '去设置智能体',
    hostApprovalMode: {
      ask: '请求批准',
      askHint: '删除和工作区外的写入都要你确认',
      auto: '替我审批',
      autoHint: '由模型代你判断，不打扰你',
      switchFailed: '切换审批模式失败'
    },
    messages: {
      enterContent: '请先输入内容!',
      replying: '正在回复中，请稍后再试!',
      steerFailed: '追加失败，请重试',
      agentSwitchedOn: '已切换到智能推理',
      agentSwitchedOff: '已切换到快速问答',
      agentSelected: '已选择智能体「{name}」',
      webSearchNotConfigured: '未配置网络搜索引擎，请先在设置中完成搜索引擎选择与接口配置。',
      webSearchEnabled: '网络搜索已开启',
      webSearchDisabled: '网络搜索已关闭',
      sessionMissing: '会话 ID 不存在',
      messageMissing: '无法获取消息 ID，请刷新页面后重试',
      stopSuccess: '已停止生成',
      stopFailed: '停止失败，请重试'
    },
    webSearch: {
      toggleOn: '开启网络搜索',
      toggleOff: '关闭网络搜索',
      notConfigured: '未配置网络搜索引擎'
    }
  },
  manualEditor: {
    defaultTitlePrefix: '新建文档',
    noDocumentKnowledgeBases: '暂无可用的文档型知识库，请先创建一个文档型知识库',
    actions: {
      cancel: '取消',
      saveDraft: '暂存草稿',
      publish: '发布入库'
    },
    loading: {
      content: '正在加载内容',
      preparing: '正在准备编辑器'
    },
    status: {
      draftTag: '当前状态：草稿',
      publishedTag: '当前状态：已发布',
      lastUpdated: '最近更新：{time}',
      counter: '{chars} 字 · {lines} 行'
    },
    form: {
      knowledgeBasePlaceholder: '请选择知识库',
      titleLabel: '知识标题',
      knowledgeBaseLabel: '目标知识库',
      titlePlaceholder: '请输入标题',
      contentPlaceholder: '支持 Markdown 语法，可使用 # 标题、列表、代码块等'
    },
    success: {
      draftSaved: '草稿已保存',
      published: '知识已发布并开始索引'
    },
    warning: {
      selectKnowledgeBase: '请选择目标知识库',
      enterTitle: '请输入知识标题',
      enterContent: '请输入知识内容',
      contentTooShort: '内容过短，建议补充更多信息后再发布'
    },
    error: {
      fetchDetailFailed: '获取知识详情失败',
      saveFailed: '保存失败，请稍后重试'
    },
    labels: {
      currentKnowledgeBase: '当前知识库'
    },
    section: {
      content: '知识内容'
    },
    title: {
      edit: '编辑 Markdown 知识',
      create: '在线编辑 Markdown 知识'
    },
    preview: {
      empty: '暂无内容'
    },
    view: {
      edit: '编辑',
      split: '分屏',
      preview: '预览',
      splitUnavailable: '宽度不足，拖宽抽屉或全屏后可用分屏',
      groupLabel: '编辑区视图'
    },
    shortcuts: {
      title: '快捷键',
      continueList: '列表内自动续行',
      indent: '缩进 / Shift+Tab 反缩进'
    },
    toolbar: {
      bold: '加粗',
      italic: '斜体',
      strike: '删除线',
      inlineCode: '行内代码',
      heading1: '一级标题',
      heading2: '二级标题',
      heading3: '三级标题',
      bulletList: '无序列表',
      orderedList: '有序列表',
      taskList: '任务列表',
      blockquote: '引用',
      codeBlock: '代码块',
      link: '插入链接',
      image: '插入图片',
      table: '插入表格',
      horizontalRule: '分割线',
      headingGroup: '标题',
      insertGroup: '插入'
    },
    table: {
      column1: '列1',
      column2: '列2',
      cell: '内容'
    },
    placeholders: {
      heading: '标题{level}',
      listItem: '列表项',
      taskItem: '任务项',
      quote: '引用内容',
      code: '代码内容',
      linkText: '链接文本',
      imageAlt: '描述',
      bold: '加粗文本',
      italic: '斜体文本',
      strike: '删除线',
      inlineCode: 'code'
    },
    assistant: {
      button: '助手',
      tooltip: '让助手帮你写',
      continue: '续写',
      outline: '生成大纲',
      polish: '润色全文',
      summarize: '总结要点',
      open: '打开助手',
      prompts: {
        continue: '接着正文末尾续写一段，与前文衔接。',
        outline: '根据标题和现有内容，为这篇文档拟一份结构清晰的大纲，写在正文开头。',
        polish: '润色正文：修正错别字和不通顺的句子，不改变原意，分段修改。',
        summarize: '总结这篇文档的要点，在对话里回复，不要修改正文。'
      }
    }
  },
  file: {
    upload: '上传文件'
  },
  mentionDetail: {
    readOnlyFromAgent: '仅在此对话中只读，不显示在知识库列表中',
    faqCount: '共 {count} 条问答',
    kbCount: '共 {count} 个文档',
    mcpToolCount: '共 {count} 个工具',
    mcpNotSynced: '尚未同步工具',
    mcpStale: '需重新同步',
    belongsToKb: '所属知识库：',
    belongsToOrg: '所属空间：',
    noCompatibleKbForAgent: '当前智能体的工具与作用域内知识库的能力不匹配，暂无可引用的知识库。',
    tag: '标签',
    searchPlaceholder: '搜索知识库、文件、技能等',
    searchInGroup: '在{group}中搜索…',
    typeToSearch: '在 {\'@\'} 后继续输入以搜索…',
    viewAll: '查看全部',
    back: '返回'
  },
  mentionBrowser: {
    browse: '按目录浏览',
    path: '目录路径',
    root: '根目录',
    searchFolder: '搜索当前目录',
    searchKb: '搜索知识库',
    subtree: '搜索包含当前目录及其子目录。',
    wholeKb: '当前仍选中了整库，选择单文件不会缩小该范围。',
    tags: '已有标签仍会过滤所选文件。',
    folderCount: '含子目录共 {count} 个文档',
    selected: '已选择',
    deleting: '正在删除',
    unsupported: '当前智能体不支持此格式',
    forbidden: '你已无权访问此内容。',
    missing: '目录已失效，请返回并重新选择。',
    error: '目录加载失败，请重试。',
    retry: '重试',
    empty: '当前视图没有文件。',
    previous: '上一页',
    next: '下一页',
    page: '第 {page} 页 · 共 {total} 个文档'
  },
  common: {
    confirm: '确认',
    cancel: '取消',
    fullscreen: '全屏',
    exitFullscreen: '退出全屏',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    copy: '复制',
    copied: '已复制',
    copySuccess: '已复制',
    loading: '加载中...',
    noMoreData: '已加载全部内容',
    loadMore: '加载更多',
    error: '错误',
    success: '成功',
    failed: '失败',
    selectAll: '全选',
    yes: '是',
    no: '否',
    close: '关闭',
    back: '返回',
    next: '下一步',
    finish: '完成',
    all: '全部',
    clear: '清空',
    on: '开启',
    off: '关闭',
    confirmDelete: '确认删除',
    deleteFailed: '删除失败',
    operationFailed: '操作失败',
    file: '文件',
    skill: '技能',
    knowledgeBase: '知识库',
    noResult: '无结果',
    remove: '移除',
    avatar: '头像',
    defaultUser: '用户',
    copyFailed: '复制失败',
    retry: '重试',
    expand: '展开',
    unsavedChanges: {
      title: '有未保存的更改',
      body: '关闭后当前修改将丢失，确定要关闭吗？',
      discard: '放弃更改',
      keepEditing: '继续编辑'
    }
  },
  authStore: {
    errors: {
      parseUserFailed: '解析用户信息失败',
      parseTenantFailed: '解析空间信息失败',
      parseKnowledgeBasesFailed: '解析知识库列表失败',
      parseCurrentKnowledgeBaseFailed: '解析当前知识库失败'
    }
  },
  auth: {
    account: '账号',
    accountPlaceholder: '请输入账号',
    accountRequired: '请输入账号',
    accountDescription: '用于登录平台的账号',
    login: '登录',
    logout: '退出',
    oidcLogin: '使用 OIDC 登录',
    oidcLoginWithProvider: '使用 {provider} 登录',
    redirectingToOIDC: '正在跳转到身份提供商...',
    orContinueWith: '或使用以下方式继续',
    oidcLoginFailed: 'OIDC 登录失败',
    username: '用户名',
    email: '邮箱',
    password: '密码',
    confirmPassword: '确认密码',
    loginSuccessTitle: '登录成功',
    loginSuccessContent: '欢迎，你已进入 {name}',
    loggingIn: '登录中...',
    register: '注册',
    registering: '注册中...',
    createAccount: '创建账户',
    haveAccount: '已有账户？',
    backToLogin: '返回登录',
    loginHint: '登录以继续使用；首次使用请在下方创建账户。',
    firstTime: '首次使用？',
    registerSuccess: '注册成功，请登录',
    registerFailed: '注册失败',
    registerSubtitle: '创建账户，开始使用知识库',
    emailPlaceholder: '输入邮箱地址',
    passwordPlaceholder: '输入密码',
    confirmPasswordPlaceholder: '再次输入密码',
    usernamePlaceholder: '输入用户名',
    emailRequired: '请输入邮箱地址',
    emailInvalid: '请输入正确的邮箱格式',
    passwordRequired: '请输入密码',
    passwordMinLength: '密码至少8个字符',
    passwordMaxLength: '密码不能超过1024个字符',
    passwordMustContainLetter: '密码必须包含字母',
    passwordMustContainLowercaseLetter: '密码必须包含小写字母',
    passwordMustContainUppercaseLetter: '密码必须包含大写字母',
    passwordMustContainNumber: '密码必须包含数字',
    passwordMustContainSpecialChar: '密码必须包含特殊字符：{specialChars}',
    usernameRequired: '请输入用户名',
    usernameMinLength: '用户名至少2个字符',
    usernameMaxLength: '用户名不能超过20个字符',
    usernameInvalid: '用户名只能包含字母、数字、下划线和中文字符',
    confirmPasswordRequired: '请确认密码',
    passwordMismatch: '两次输入的密码不一致',
    loginError: '登录错误，请检查账号或密码',
    loginErrorRetry: '登录错误，请稍后重试',
    registerError: '注册错误，请稍后重试',
    workspaceOnboarding: {
      title: '选择你的工作空间',
      description: '创建个人空间后即可继续使用。',
      create: '创建空间',
      invitations: '查看邀请',
      loadingPolicy: '正在确认可用的空间加入方式…',
      policyLoadFailed: '暂时无法获取空间权限，请检查网络后重试。',
      retry: '重新加载',
      inviteOnlyTitle: '等待加入工作空间',
      inviteOnlyDescription: '当前系统不开放个人创建空间。你可以查看并接受管理员发来的空间邀请。',
      inviteOnlyNotice: '此账户只能通过邀请加入已有空间',
      help: '你现在可以创建空间，也可以稍后回来接受邀请。',
      inviteOnlyHelp: '还没有邀请？请把你的注册邮箱提供给空间管理员，由管理员向你发送邀请。'
    }
  },
  inviteRegister: {
    bannerTitle: '您被邀请加入「{tenant}」',
    bannerHint: '填写下方信息完成注册，注册成功后将自动加入该团队。',
    bannerHintLogin: '登录后将自动加入该团队。',
    loading: '正在校验邀请链接…',
    invalidTitle: '邀请链接无效或已撤销',
    invalidBody: '请联系邀请人重新发送链接，或前往登录使用现有账号。',
    backToLogin: '返回登录',
    title: '完成注册',
    subtitle: '您被邀请加入「{tenant}」',
    email: '邮箱',
    emailPlaceholder: 'your{\'@\'}example.com',
    emailHint: '用您自己的邮箱注册即可。',
    emailInvalid: '请输入有效的邮箱地址',
    username: '姓名',
    usernamePlaceholder: '请输入您的姓名',
    password: '设置密码',
    passwordPlaceholder: '至少 6 位',
    confirmPassword: '确认密码',
    submit: '完成注册',
    submitting: '提交中…',
    success: '注册成功，正在进入工作空间…',
    joined: '已加入该团队',
    failed: '注册失败，请稍后重试',
    usernameRequired: '请输入姓名',
    passwordTooShort: '密码至少 6 位',
    passwordMismatch: '两次输入的密码不一致'
  },
  initialization: {
    skip: '跳过',
    next: '下一步'
  },
  graphSettings: {
    title: '知识图谱配置',
    description: '配置实体-关系提取功能，自动从文本中抽取实体和关系构建知识图谱（注意：这与 Wiki 知识库中的「页面链接图谱」是两回事——前者是基于 LLM 的实体-关系图，后者是 Wiki 页面之间的引用关系图）',
    enableLabel: '启用实体关系提取',
    enableDescription: '开启后将自动从文本中提取实体和关系',
    tagsLabel: '关系类型',
    tagsDescription: '定义要提取的关系类型标签，多个标签用逗号分隔',
    tagsPlaceholder: '输入关系类型，如：工作于、同事、朋友等',
    generateRandomTags: '生成随机标签',
    sampleTextLabel: '示例文本',
    sampleTextDescription: '用于测试实体关系提取的示例文本',
    sampleTextPlaceholder: '输入一段包含实体和关系的文本...',
    customInstructionsLabel: '额外提取要求',
    customInstructionsDescription: '补充领域范围、实体筛选和属性提取要求；系统仍负责结构化输出协议',
    customInstructionsPlaceholder: '例如：重点提取合同主体、金额、履约期限和违约责任…',
    generateRandomText: '生成随机文本',
    entityListLabel: '实体列表',
    entityListDescription: '从文本中提取的实体及其属性',
    nodeNamePlaceholder: '输入实体名称',
    attributePlaceholder: '输入属性值',
    addAttribute: '添加属性',
    manageEntitiesLabel: '管理实体',
    manageEntitiesDescription: '添加或删除实体节点',
    addEntity: '添加实体',
    relationListLabel: '关系列表',
    relationListDescription: '定义实体之间的关系连接',
    selectEntity: '选择实体',
    selectRelationType: '选择关系类型',
    manageRelationsLabel: '管理关系',
    manageRelationsDescription: '添加或删除实体间的关系',
    addRelation: '添加关系',
    extractActionsLabel: '提取操作',
    extractActionsDescription: '执行实体关系提取或管理示例数据',
    startExtraction: '开始提取',
    extracting: '提取中...',
    defaultExample: '默认示例',
    clearExample: '清除示例',
    completeModelConfig: '请先完成模型配置',
    tagsGenerated: '标签生成成功',
    tagsGenerateFailed: '标签生成失败',
    textGenerated: '文本生成成功',
    textGenerateFailed: '文本生成失败',
    pleaseInputText: '请先输入示例文本',
    extractSuccess: '实体关系提取成功',
    extractFailed: '实体关系提取失败',
    exampleLoaded: '示例已加载',
    exampleCleared: '示例已清除',
    checkingAvailability: '正在检查知识图谱服务…',
    checkAvailabilityFailed: '无法检查知识图谱服务，请重试。',
    disabledWarning: '知识图谱数据库未启用，实体关系提取功能将无法使用',
    howToEnable: '如何启用知识图谱？'
  },
  retrievalSettings: {
    title: '搜索设置',
    description: '配置知识库搜索和消息搜索的全局检索参数，参数直接透传给 ContextDB 官方检索接口',
    topKLabel: '检索返回数量 (Top K)',
    topKDescription: '单次检索返回的片段数，范围 1–10；ContextDB 官方默认 5',
    similarityThresholdLabel: '相似度阈值',
    similarityThresholdDescription: '相关性低于该阈值的片段会被过滤，范围 0–1；ContextDB 官方默认 0.6',
    vectorWeightLabel: '向量权重',
    vectorWeightDescription: '向量与关键词混合检索的平衡权重，范围 0–1；ContextDB 官方默认 0.7',
    queryRewriteLabel: '查询改写',
    queryRewriteDescription: '检索前由 ContextDB 用 LLM 改写查询以提升召回；官方默认关闭，本平台默认开启',
    toasts: {
      saveSuccess: '检索配置已保存',
      saveFailed: '保存配置失败: {message}'
    }
  },
  defaultSettings: {
    saving: '保存中',
    loadFailed: '默认设置加载失败，请重试后再编辑。',
    title: '默认配置',
    readOnly: '仅空间管理员可以修改，你可以查看当前生效的默认值。',
    webSearchGroup: '网络搜索',
    toasts: {
      saveFailed: '保存失败：{message}'
    },
    webSearch: {
      label: '默认搜索引擎',
      description: '未单独指定搜索引擎的智能体开启联网搜索时使用。',
      unset: '未设置默认搜索引擎，未单独指定搜索引擎的智能体将无法联网搜索。',
      placeholder: '选择搜索引擎'
    },
    hints: {
      workspace: '使用空间设置。',
      system: '未设置，当前使用系统默认：{name}',
      auto: '未设置，当前自动使用首个可用模型：{name}',
      followChat: '未设置，跟随默认对话模型：{name}',
      staleFallback: '所选模型已删除或不可用，当前回退到：{name}',
      staleNone: '所选模型已删除或不可用，且没有可回退的模型。'
    },
    slots: {
      asr: {
        label: '默认语音识别模型',
        description: '用于音视频转写的默认选择。',
        none: '空间内没有可用的语音识别模型，音视频转写不可用。'
      },
      vlm: {
        label: '默认视觉模型',
        description: '用于图片理解和多模态解析的默认选择。',
        none: '空间内没有可用的视觉模型，图片理解不可用。'
      },
      rerank: {
        label: '默认 Rerank 模型',
        description: '未单独配置重排模型的检索和内置智能体使用。',
        none: '空间内没有可用的 Rerank 模型，检索将按召回顺序返回。'
      },
      embedding: {
        label: '默认 Embedding 模型',
        description: '新建知识库时默认选用。已有知识库不受影响。',
        none: '空间内没有可用的 Embedding 模型，无法新建知识库。'
      },
      utility: {
        label: '轻量生成模型',
        description: '用于生成会话标题、MCP 服务使用说明等短文本任务，可选更快更便宜的模型。',
        none: '空间内没有可用的对话模型，标题和说明生成将无法使用。'
      },
      chat: {
        label: '默认对话模型',
        description: '新建智能体和问答默认使用，也作为后台任务的兜底模型。',
        none: '空间内没有可用的对话模型，问答和后台生成将无法使用。'
      }
    }
  },
  envVarSettings: {
    host: {
      title: '环境变量'
    }
  },
  settings: {
    modelManagement: '模型管理',
    autoCheckUpdate: '自动下载更新',
    autoCheckUpdateDesc: '开启后自动检查并在后台下载最新版本安装包。',
    parserEngine: '解析引擎',
    mcpService: 'MCP服务',
    workspaceSettings: '空间设置',
    capabilityUnavailable: '当前部署不支持此功能，已返回可用页面。',
    hostApprovalDefault: {
      title: '默认执行权限审批',
      description: '智能体要删除文件，或写入工作区以外时，用这里决定是每次问你，还是由模型替你审批。新会话按这个开始；当前会话可在输入框左侧切换。'
    },
    storage: {
      title: '存储引擎',
      engineLocal: 'Local（本地）',
      engineCos: '腾讯云 COS',
      engineTos: '火山引擎 TOS',
      engineOss: '阿里云 OSS'
    },
    parser: {
      title: '解析引擎'
    },
    roleDenied: {
      title: '权限不足',
      desc: '你当前的角色无权访问此设置项。请联系本空间的管理员获取所需角色。'
    },
    navGroups: {
      systemAdministration: '系统管理'
    },
    skills: {
      nativeUsage: '在智能体配置中选择技能包。脚本执行需要 OpenSandbox 及相应依赖；目录可用不代表依赖已安装。',
      addSourceDescription: '导入包含唯一 SKILL.md 的技能目录，保留资料和脚本文件；只登记内容，不执行安装。',
      title: '技能管理',
      description: '管理技能包目录。选择后由官方 SkillsMiddleware 加载指令与资料；上传不会安装依赖。',
      helpTooltip: '目录保存指令、资料和脚本；脚本复制到会话沙箱运行，依赖由部署镜像提供。',
      addSkill: '添加技能',
      addStepRegister: '登记',
      addFileSelected: '已选择 {name}',
      addClearFile: '清除',
      emptyDesc: '还没有技能包。上传 ZIP 或填写来源添加到目录。',
      deleteCatalog: '从目录删除',
      deleteCatalogConfirm: '确定从目录删除「{name}」？历史安装记录保留；存在历史引用时不能删除。',
      deleteSuccess: '已从目录删除',
      registerAccepted: '已添加到目录',
      loadFailed: '加载失败'
    },
    sandbox: {
      title: '沙箱配置',
      skillUploadClick: '点击上传 zip 压缩包',
      skillUploadDrag: '或将文件拖到此处',
      skillSourceSection: '从来源安装',
      skillSourceSectionHint: '粘贴 ClawHub、GitHub 或 SkillHub 链接，或 {\'@\'}owner/slug。压缩包不超过 {size} MB。',
      skillUploadSection: '上传本地压缩包',
      skillUploadSectionHint: '把包含 SKILL.md 的 zip 拖到下方，或点击选择文件。压缩包不超过 {size} MB。',
      skillSourcePlaceholder: 'ClawHub 用 {\'@\'}owner/slug，GitHub / SkillHub 请粘贴完整链接',
      skillSourceFailed: '从托管平台安装技能失败',
      skillUploadFailed: '技能上传失败',
      skillBundleTooLarge: '技能压缩包不能超过 {size} MB。',
      skillBundleTooManyFiles: '技能目录里的文件不能超过 {count} 个。',
      skillBundleTooManyZipEntries: '压缩包条目不能超过 {count} 个。',
      installCommandRunning: '命令执行中',
      skillFiles: '查看文件',
      skillFilesTitle: '文件',
      skillFilesEmpty: '该技能还没有可查看的文件。',
      skillFilesLoadFailed: '加载技能文件失败',
      skillFilesFileLoadFailed: '无法读取该文件',
      skillFilesBinary: '该文件是二进制内容，无法在线预览。',
      skillFilesTruncated: '文件较大，仅显示前一部分。',
      skillFilesSelectHint: '选择左侧文件以查看内容',
      skillFilesPreview: '预览',
      skillFilesSource: '源码',
      skillDisabled: '已禁用技能',
      installCommandWaiting: '等待命令输出，耗时持续更新。'
    }
  },
  agent: {
    taskLabel: '任务:',
    think: '思考',
    copy: '复制',
    addToKnowledgeBase: '添加到知识库',
    updatePlan: '更新计划',
    webSearchFound: '找到 <strong>{count}</strong> 个网络搜索结果',
    toolFallback: '工具',
    stepsCompleted: '已完成 <strong>{steps}</strong> 个步骤',
    reasoningRounds: '思考 <strong>{rounds}</strong> 轮',
    earlierSteps: '已完成 {count} 个步骤',
    viewReasoning: '查看思路',
    toolCalls: '调用 <strong>{tools}</strong> 次工具',
    durationSuffix: '耗时 <strong>{duration}</strong>',
    stepSummarySeparator: ' · ',
    contextCompacted: '压缩上下文',
    contextCompactedSummary: '{before} → {after} tokens',
    contextCompactedDegraded: '摘要不可用，已保留原始记录',
    title: '智能体',
    subtitle: '配置和管理您的智能体，自定义对话行为和能力',
    createAgent: '创建智能体',
    builtin: '内置',
    disabled: '已停用',
    disable: '停用',
    enable: '启用',
    noDescription: '暂无描述',
    selectAgent: '选择智能体',
    noAgents: '暂无智能体',
    manageAgents: '管理',
    builtinAgents: '内置智能体',
    customAgents: '自定义智能体',
    selector: {
      title: '选择智能体',
      current: '当前',
      goToSettings: '设置',
      sharedLabel: '共享',
      notReadyHint: '尚未就绪，还需配置：{items}',
      notReadyStatus: '待配置',
      configureAction: '去配置',
      sharedNotReadyContact: '请联系分享方管理员完成配置',
      capabilitiesSection: '能力',
      webSearchCapability: '网络搜索',
      imageUploadCapability: '图片上传',
      capabilityEnabled: '开启',
      capabilityDisabled: '关闭',
      capabilitySupported: '支持',
      capabilityUnsupported: '不支持',
      capabilityUnconfigured: '未配置'
    },
    editor: {
      assistantChanged: '助手已修改此智能体，请重新打开以查看最新设置。',
      assistantDeleted: '助手已删除此智能体。',
      reasoningEffortUnsupported: '当前所选模型不支持思考，除「关闭」外的选项将被忽略。',
      reasoningEffortAlwaysOn: '当前所选模型始终开启思考，无法关闭，只能调整思考强度。',
      createTitle: '创建智能体',
      editTitle: '编辑智能体',
      basicInfo: '基本信息',
      basicInfoDesc: '配置智能体的名称、描述与运行模式',
      promptsConfig: '提示词',
      promptsConfigDesc: '配置系统提示词、上下文模板、意图/改写/兜底提示词',
      modelConfig: '模型配置',
      modelConfigDesc: '配置对话模型、ReRank 等辅助模型及生成参数',
      toolsConfig: '工具配置',
      toolsConfigDesc: '配置 Agent 可以使用的工具',
      knowledgeConfig: '知识库',
      knowledgeConfigDesc: '配置智能体可访问的知识库范围与 FAQ 策略',
      agentId: '智能体 ID',
      agentIdDesc: 'API 集成时可使用此 ID 指定智能体',
      name: '名称',
      namePlaceholder: '请输入智能体名称',
      nameRequired: '请输入智能体名称',
      systemPromptRequired: '请输入系统提示词',
      modelRequired: '请选择模型',
      queryMissingInRewrite: '改写用户提示词必须包含 {\'{{\'}query{\'}}\'} 占位符',
      queryMissingInFallback: '兜底提示词必须包含 {\'{{\'}query{\'}}\'} 占位符',
      description: '描述',
      descriptionPlaceholder: '请输入智能体描述',
      normalDesc: '快速响应，直接回答问题',
      agentDesc: '多步思考，深度分析复杂问题',
      model: '模型',
      modelPlaceholder: '请选择模型',
      systemPrompt: '系统提示词',
      systemPromptPlaceholder: '自定义系统提示词，定义智能体的行为和角色（使用 {\'{{\'}web_search_status{\'}}\'} 占位符动态控制网络搜索行为）',
      contextTemplateRequired: '请输入上下文模板',
      temperature: '温度',
      thinking: '思考模式',
      citationEnabled: '输出来源引用',
      citationEnabledDesc: '在最终回答中展示知识库和网页来源；关闭后仍会正常检索和使用证据',
      mode: '运行模式',
      knowledgeBases: '关联知识库',
      allKnowledgeBases: '全部知识库',
      selectedKnowledgeBases: '指定知识库',
      noKnowledgeBase: '不使用知识库',
      selectKnowledgeBases: '选择知识库',
      selectKnowledgeBasesDesc: '选择要关联的知识库（包括协作知识库）',
      myKnowledgeBases: '我的知识库',
      sharedKnowledgeBases: '协作知识库',
      retrieveKBOnlyWhenMentioned: '仅在 {\'@\'} 提及时检索',
      retrieveKBOnlyWhenMentionedDesc: '关闭：自动检索已配置的知识库，开启：仅当用户 {\'@\'} 提及时才检索',
      rerankModel: 'ReRank 模型',
      rerankModelDesc: '用于对知识库检索结果进行重排序，提高回答准确性',
      rerankModelPlaceholder: '请选择 ReRank 模型',
      rerankModelOptionalHint: '当前作用域内暂无 RAG 类型知识库，可不填；后续若加入 RAG 知识库，将自动使用空间默认重排模型，仍建议显式配置。',
      maxIterations: '主 Agent 单轮模型调用上限',
      maxIterationsLimit: '限制',
      maxIterationsUnlimited: '不限制',
      allowedTools: '允许的工具',
      retrievalStrategy: '检索策略',
      contextTemplate: '上下文模板',
      contextTemplatePlaceholder: '自定义上下文模板...',
      queryUnderstandModel: '问题理解模型',
      queryUnderstandModelPlaceholder: '留空则复用主对话模型',
      rewritePromptSystem: '改写系统提示词',
      rewritePromptSystemPlaceholder: '留空使用系统默认提示词',
      rewritePromptUser: '改写用户提示词',
      rewritePromptUserPlaceholder: '留空使用系统默认提示词',
      maxCompletionTokens: '最大生成Token数',
      maxCompletionTokensDefault: '默认',
      maxCompletionTokensCustom: '自定义',
      fallbackStrategy: '兜底策略',
      fallbackResponse: '固定回复内容',
      fallbackResponsePlaceholder: '抱歉，我无法回答这个问题。',
      fallbackPrompt: '兜底提示词',
      fallbackPromptPlaceholder: '留空使用系统默认提示词',
      skillsConfig: '技能',
      skillsSelection: '技能列表',
      skillsAll: '全部',
      skillsSelected: '指定',
      skillsNone: '禁用',
      skillsGroupUnavailable: '不可用',
      noSkillsAvailable: '空间目录里还没有技能。',
      goSandboxSettings: '管理沙箱',
      sandboxBackend: '运行沙箱',
      memoryEnabled: '长期记忆',
      nativeRuntime: {
        adoptRuntime: '采用当前运行设置',
        incompatible: '当前配置包含与本部署运行策略不兼容的值。请先核对下列变动，采用后仅修改草稿，保存后生效。',
        adoptQuick: '采用当前原生快速问答设置',
        changesPending: '以下变动已应用到草稿，保存后生效。',
        removed: '移除此字段',
        defaultsUnavailable: '无法取得当前运行默认配置，暂不能保存。请重试加载。',
        retry: '重新加载',
        resolveBeforeSave: '请先处理不兼容配置，再保存。',
        quickDesc: '快速问答通过原生 Agent 按需检索与回答，使用独立的模型调用次数上限。',
        promptDesc: '配置当前模式使用的系统提示词或模板引用'
      },
      postCreateHint: {
        title: '创建成功',
        footer: '可继续调整配置，设置共享与发布渠道，完成后点击「保存并关闭」。'
      },
      buttons: {
        create: '创建智能体',
        saveAndClose: '保存并关闭'
      }
    },
    messages: {
      created: '已创建智能体',
      updated: '智能体已更新',
      deleted: '智能体已删除',
      deleteFailed: '删除失败',
      saveFailed: '保存失败',
      copied: '已复制智能体',
      copyFailed: '复制失败',
      disabled: '已停用',
      enabled: '已启用'
    },
    delete: {
      confirmTitle: '删除智能体',
      confirmMessage: '确定要删除智能体「{name}」吗？此操作不可恢复。'
    },
    shareScope: {
      title: '共享范围说明',
      desc: '空间成员以只读方式使用该智能体，将遵循您当前配置的能力与资源；您对智能体的修改会同步给已共享的空间。如需允许空间成员编辑知识库内容，请将知识库共享到空间。',
      knowledgeBase: '知识库',
      chatModel: '对话模型',
      rerankModel: '重排模型',
      webSearch: '网络搜索',
      mcp: 'MCP 服务',
      kbAll: '全部知识库',
      kbSelected: '指定 {count} 个知识库',
      kbNone: '不使用',
      modelConfigured: '已配置',
      modelNotSet: '未配置',
      enabled: '开启',
      disabled: '关闭',
      mcpAll: '全部服务',
      mcpSelected: '指定 {count} 个服务',
      mcpNone: '不使用'
    },
    detail: {
      title: '智能体详情',
      useInChat: '在对话中使用'
    },
    empty: {
      title: '暂无自定义智能体',
      description: '点击右上角按钮创建您的第一个智能体',
      sharedTitle: '暂无共享智能体',
      sharedDescription: '您可以加入空间或请求他人将智能体共享给您',
      favoritesTitle: '暂无收藏',
      favoritesDescription: '在智能体卡片右上角点击星标即可收藏',
      recentsTitle: '暂无最近访问',
      recentsDescription: '最近使用过的智能体会出现在这里'
    },
    sections: {
      builtin: '内置',
      mine: '我创建的',
      tenantOthers: '本空间 · 其他成员',
      tenantReadonly: '本空间 · 仅查看',
      sharedByMe: '我共享的',
      sharedEditable: '共享给我 · 可编辑',
      sharedReadonly: '共享给我 · 仅查看'
    },
    tabs: {
      sharedToMe: '共享给我'
    },
    features: {
      webSearch: '支持网络搜索',
      knowledgeBase: '关联知识库',
      mcp: '支持MCP服务',
      multiTurn: '多轮对话'
    },
    mode: {
      normal: '快速问答',
      agent: '智能推理'
    },
    type: {
      normal: '快速问答',
      agent: '智能推理'
    },
    capabilities: {
      kbCount: '指定 {count} 个知识库',
      kbAll: '可访问全部知识库',
      mcpEnabled: '启用 MCP 服务',
      multiTurn: '多轮对话'
    },
    artifactDrawer: {
      buttonTitle: '查看本次生成的文件',
      title: '生成的文件',
      empty: '本次未生成可下载的文件',
      preview: '预览',
      previewBack: '返回列表',
      collecting: '正在保存生成的文件…',
      delete: '删除',
      deleteTitle: '删除这个文件？',
      deleteConfirm: '将永久删除「{name}」，包括已保存的文件内容，且无法恢复。',
      deleted: '文件已删除',
      deleteFailed: '删除失败，请稍后重试',
      download: '下载',
      downloadFailed: '下载失败，请稍后重试',
      inlinePreviewHint: '点击预览',
      inlineMissing: '文件不可用',
      inlineDeleted: '文件已删除'
    }
  },
  knowledgeStages: {
    expandBranch: '展开子项',
    collapseBranch: '收起子项',
    resizeDrawer: '拖拽调整面板宽度',
    status: {
      pending: '等待中',
      running: '进行中',
      finalizing: '优化中',
      done: '已完成',
      failed: '失败',
      skipped: '已跳过',
      cancelled: '已取消'
    },
    stage: {
      docreader: '文档解析',
      chunking: '分块',
      embedding: '向量化',
      multimodal: '多模态识别',
      postprocess: '后处理'
    },
    stall: {
      title: '已 {minutes} 分钟没有进展，可能已卡住'
    },
    processConfig: {
      title: '本次解析配置'
    }
  },
  uploadConfirm: {
    imageEmbeddingModel: '图像索引 Embedding 模型',
    imageIndexInherited: '图像索引使用知识库绑定的 Embedding 模型；如需更换，请前往知识库设置。',
    imageVectorIndex: '本次图片向量索引',
    imageVectorIndexHint: '为本次上传或重新解析的图片生成向量，不改变知识库默认配置。是否参与检索仍由知识库的“图片向量检索”开关决定。',
    imageVectorRequiresIndex: '请先在知识库设置中开启向量索引。',
    documentSummary: '文档摘要',
    documentSummaryDescription: '为本次导入的文档选择是否自动生成摘要。',
    generateSummary: '生成文档摘要',
    generateSummaryHint: '默认开启。关闭后跳过摘要生成，文档解析、索引及其他处理步骤仍按配置执行。',
    title: '上传文档确认',
    parseConfig: '解析配置',
    configNav: '解析配置导航',
    navParserDefault: '默认',
    navParserCustomized: '已自定义',
    moreOptions: '更多处理选项',
    summaryParentChildShort: '父子分块',
    summaryParserForceScanned: '扫描件解析',
    summaryQuestionCountValue: '{count} 个',
    summaryGraphTagsValue: '{count} 个',
    navChunkingSummary: '分块 {size}',
    statusOn: '已开启',
    statusOff: '未开启',
    notSet: '未设置',
    summaryNoTags: '未设置',
    summaryTagsCount: '{count} 个标签',
    confirm: '确认上传并解析',
    cancel: '取消',
    tabTags: '文档标签',
    tagsDescription: '为本批次导入的所有文档选择标签，可多选',
    tagsPlaceholder: '请选择标签（可多选）',
    tagsEmpty: '当前知识库暂无标签，可上传后在标签管理中创建',
    tagsLoadFailed: '标签加载失败，可稍后在文档列表中设置',
    noItems: '请至少添加一个文件或 URL',
    urlItemLabel: 'URL',
    urlAdded: '已添加 URL',
    urlDuplicate: '该 URL 已在列表中',
    statusNeedsSetup: '待配置',
    multimodalSetupHint: '含图片内容，请启用多模态并选择模型',
    asrSetupHint: '含音频内容，请启用语音识别并选择模型',
    vlmModelRequired: '请配置多模态模型',
    asrModelRequired: '请配置语音识别模型',
    vlmModelSelectRequired: '已启用多模态，请选择 VLM 模型',
    asrModelSelectRequired: '已启用语音识别，请选择 ASR 模型',
    continueAdd: '继续添加',
    destinationLabel: '上传位置',
    destinationChange: '更改上传位置',
    filesAdded: '已添加 {count} 个文件',
    filesAllDuplicate: '所选文件已在列表中',
    titleManual: '在线编辑发布确认',
    confirmManual: '确认发布并解析',
    titleReparse: '重新解析确认',
    confirmReparse: '确认并重新解析',
    reparseSource: '待重新解析文档',
    reparseHint: '将沿用上次解析的配置，可在此调整',
    manualCharCount: '{count} 个字符',
    pdfForceScanned: {
      label: '按扫描件解析 PDF',
      description: '适用于网页打印、扫描件、图片型 PDF。开启后会逐页 OCR，解析更完整但耗时和模型调用更多。'
    }
  },
  knowledgeBase: {
    videosFilteredNoVLM: '已跳过 {count} 个视频文件（暂不支持视频上传）',
    importURL: '导入网页',
    addDocument: '添加文档',
    importURLTitle: '导入网页',
    urlRequired: '请输入URL',
    invalidURL: '请输入有效的URL',
    urlLabel: 'URL地址',
    urlPlaceholder: '请输入网页URL，例如：https://example.com',
    urlTip: '支持导入各类网页内容，系统会自动提取和解析网页中的文本内容',
    channelLabel: '来源渠道',
    channelWeb: '网页端',
    channelApi: 'API',
    channelBrowserExtension: '浏览器插件',
    channelWechat: '微信',
    channelWecom: '企业微信',
    channelFeishu: '飞书',
    channelDingtalk: '钉钉',
    channelSlack: 'Slack',
    channelIm: 'IM 渠道',
    channelConfluence: 'Confluence',
    channelGitLab: 'GitLab',
    channelNextcloud: 'Nextcloud',
    channelSeafile: 'Seafile',
    channelIma: '腾讯 IMA',
    channelUnknown: '未知',
    selectedCount: '已选 {count} 项',
    pdfDocFormat: 'pdf、doc 格式文件，不超过{size}M',
    textMarkdownFormat: 'text、markdown格式文件，不超过{size}M',
    dragFileNotText: '请拖拽文件而不是文本或链接',
    searchPlaceholder: '搜索知识库...',
    noMatch: '未找到匹配的知识库',
    noKnowledge: '暂无可用知识库',
    loadingFailed: '加载知识库失败',
    allFilesSkippedNoEngine: '所选文件类型暂无可用解析引擎，已全部跳过',
    filesSkippedNoEngine: '{count} 个文件因无可用解析引擎被跳过',
    moveToFolder: {
      action: '移动到目录',
      newFolderPlaceholder: '输入新目录名称',
      newFolderAddRoot: '在根目录下新建子目录',
      newFolderAddUnder: '在「{folder}」下新建子目录',
      duplicate: '该目录已存在'
    },
    folderTree: {
      title: '目录',
      rootRow: '根目录'
    },
    sort: {
      title: '排序'
    },
    infoCard: {
      title: '知识库信息'
    }
  },
  resourceOrigin: {
    mine: '我创建',
    mineTooltip: '由当前用户创建',
    tenant: '本空间',
    tenantTooltip: '本空间其他成员创建',
    tenantTooltipWithCreator: '由 {creator} 创建',
    space: '共享空间',
    spaceTooltip: '来自共享空间「{space}」',
    spaceTooltipWithTenant: '来自共享空间「{space}」· 源空间 {tenant}',
    shared: '外部共享',
    sharedTooltip: '通过共享空间从其他空间访问'
  },
  listSpaceSidebar: {
    all: '全部',
    workspace: '本空间',
    spaces: '共享给我',
    favorites: '收藏',
    recents: '最近'
  },
  batchManage: {
    selectAll: '全选',
    cancel: '取消',
    delete: '删除对话',
    deleteConfirmTitle: '删除对话',
    deleteConfirmBody: '确定要删除选中的 {count} 条对话吗？删除后无法恢复。',
    deleteAllConfirmBody: '确定要删除所有对话吗？此操作无法恢复。',
    deleteSuccess: '已删除',
    deleteFailed: '删除失败，请稍后再试'
  },
  contextualGuide: {
    stepOf: '{current} / {total}',
    skip: '跳过',
    prev: '上一步',
    next: '下一步',
    done: '知道了',
    interactHint: '请直接点击高亮区域继续',
    chat: {
      steps: {
        done: {
          title: '开始探索吧',
          desc: '试试提一个与已上传文档相关的问题，体验带引用的精准回答。'
        },
        send: {
          title: '发送开始对话',
          desc: '发送后将创建新会话，AI 会结合知识库内容作答，并标注引用片段。'
        },
        input: {
          title: '输入你的问题',
          desc: '直接描述你想了解的内容；也可点击上方推荐问题快速开始。'
        },
        kb: {
          title: '选择知识范围',
          desc: '点击 {\'@\'} 可指定一个或多个知识库/文件，仅基于选中内容回答；不选则按当前智能体配置检索。'
        }
      }
    },
    kbDetail: {
      steps: {
        done: {
          title: '解析完成后即可使用',
          desc: '文档解析入库后，可在对话中 {\'@\'} 本知识库提问，回答会附带引用来源。'
        },
        upload: {
          title: '添加文档',
          desc: '点击此处上传文件、文件夹，或导入网页与在线编辑内容。'
        },
        intro: {
          title: '知识库还是空的',
          desc: '添加第一份资料后，才能基于它进行检索与对话。支持拖拽上传多种文档格式。'
        }
      }
    },
    agentCreate: {
      steps: {
        submit: {
          title: '保存智能体',
          desc: '确认配置后点击高亮的「确定」完成创建，即可在对话中选择该智能体。'
        },
        navTools: {
          title: '工具与 MCP（可选）',
          desc: '智能推理模式下可勾选内置工具、MCP 服务等，扩展搜索、计算等能力。'
        },
        multimodal: {
          title: '启用附件上传',
          desc: '可分别配置图片、音频上传及附件解析策略；启用图片上传时需在下方选择 VLM 模型。'
        },
        navMultimodal: {
          title: '附件上传（可选）',
          desc: '开启后，对话中可上传图片、文档、音频等附件；图片理解需先在系统设置中配置 VLLM 模型。'
        },
        navWebsearch: {
          title: '联网搜索（可选）',
          desc: '配置是否允许智能体调用外部搜索引擎补充实时信息。'
        },
        knowledge: {
          title: '知识库范围',
          desc: '「全部」适合通用助手；「指定」可限定专业领域；「不关联」则仅依赖模型自身能力或联网搜索。'
        },
        navKnowledge: {
          title: '关联知识库',
          desc: '决定智能体可检索哪些知识。默认「全部知识库」，也可改为指定库或暂不关联。'
        },
        model: {
          title: '选择模型',
          desc: '从下拉列表选择已配置的对话模型；没有合适模型时请先到系统设置添加。'
        },
        navModel: {
          title: '绑定对话模型',
          desc: '每个智能体必须指定一个 KnowledgeQA 模型作为推理引擎。'
        },
        name: {
          title: '命名与描述',
          desc: '取一个易识别的名称。智能推理模式下系统可能已预填默认名称，可按需修改。'
        },
        agentType: {
          title: '选择智能体类型',
          desc: '预设类型会自动填充系统提示词、推荐工具与知识库范围（如 Wiki 构建、数据分析等）。可按场景切换，名称与描述会随之更新。'
        },
        mode: {
          title: '选择运行模式',
          desc: '「普通模式」适合固定流程的快速问答；「智能推理」可调用工具、多步思考，适合复杂任务。'
        }
      }
    },
    agentList: {
      steps: {
        create: {
          title: '创建你的智能体',
          desc: '智能体把模型、知识库、工具与提示词组合成可复用的对话助手。点击下方高亮的「创建智能体」开始配置。'
        }
      }
    },
    kbCreate: {
      steps: {
        submit: {
          title: '创建知识库',
          desc: '点击「知道了」结束引导，无需现在创建知识库。准备好后，填写名称、确认类型与模型，再点击「创建」。'
        },
        faq: {
          title: 'FAQ 索引方式',
          desc: '配置问答对的索引模式。创建后可在本页继续添加 FAQ 条目。'
        },
        multimodalVllm: {
          title: '选择 VLM 模型',
          desc: '开启多模态后需指定 VLM（视觉语言模型）。若列表为空，请先在系统设置中添加 VLLM 类型模型。'
        },
        multimodalToggle: {
          title: '开启多模态解析',
          desc: '启用后，上传的图片类文档将使用视觉语言模型提取内容，便于检索与问答。'
        },
        navMultimodal: {
          title: '多模态 / 图片理解（可选）',
          desc: '若文档含大量图表、扫描件或需理解图片内容，可在此开启多模态并选择 VLM 模型。'
        },
        storage: {
          title: '存储引擎（可选）',
          desc: '原始文件存放位置（本地或对象存储）。默认跟随空间设置即可。'
        },
        chunking: {
          title: '分块策略（可选）',
          desc: '决定文档如何切分为检索片段。默认分块大小已针对 RAG 优化，一般无需修改。'
        },
        parser: {
          title: '解析引擎（可选）',
          desc: '控制 PDF、Office 等文件的解析方式。默认配置适用于大多数场景，有 OCR 需求时可在此调整。'
        },
        embedding: {
          title: 'Embedding 模型',
          desc: '将文本转为向量以支持语义检索。与上方索引策略中的「向量/关键词检索」配合使用。'
        },
        llm: {
          title: '对话 / 摘要模型',
          desc: '用于文档摘要、问答生成等。若列表为空，请通过下拉菜单前往系统设置添加模型。'
        },
        navModels: {
          title: '配置模型（必填）',
          desc: '知识库必须绑定对话模型；开启检索时还需 Embedding 模型。点击左侧「模型配置」进入。'
        },
        indexing: {
          title: '选择索引能力',
          desc: '默认已开启向量与关键词检索，可按需开启 Wiki 结构化索引或知识图谱。至少保留一种检索方式。'
        },
        name: {
          title: '填写名称',
          desc: '取一个便于识别的名称，例如「产品手册」或「客服 FAQ」。描述可选填。'
        },
        type: {
          title: '选择知识库类型',
          desc: '文档库适合上传 PDF、Word 等文件；FAQ 库适合问答对。创建后类型不可更改，请按需选择。'
        }
      }
    },
    tenantModels: {
      needChatModelFirst: '请先添加对话模型（KnowledgeQA），再创建智能体。',
      stepsAgent: {
        done: {
          title: '然后创建智能体',
          desc: '保存并关闭设置后，点击「创建智能体」，向导会带你配置模式、知识库与附件上传等选项。'
        },
        addModel: {
          title: '添加对话模型',
          desc: '点击「添加模型」，选择 KnowledgeQA 类型并填写接入信息。'
        },
        intro: {
          title: '需要先配置对话模型',
          desc: '创建智能体至少需要一种 KnowledgeQA（对话）模型。请先在系统设置中添加；Embedding 模型仅创建知识库时需要。'
        }
      },
      steps: {
        done: {
          title: '添加完成后继续',
          desc: '模型保存后关闭设置页，即可点击「新建知识库」；创建向导会引导你完成类型、索引与模型绑定。'
        },
        addModel: {
          title: '添加模型',
          desc: '点击「添加模型」，分别配置 KnowledgeQA（对话）与 Embedding 类型。Lite 用户可使用 Ollama 拉取本地模型。'
        },
        intro: {
          title: '需要先配置模型',
          desc: '创建文档知识库至少需要：一个对话模型（用于摘要与问答）和一个 Embedding 模型（用于向量检索）。请先在系统设置中添加。'
        }
      }
    },
    kbList: {
      steps: {
        create: {
          title: '创建第一个知识库',
          desc: '知识库用来存放文档与 FAQ。点击下方高亮的「新建知识库」按钮，我们会带你完成表单填写。'
        }
      }
    }
  },
  newUserGuide: {
    stepOf: '{current} / {total}',
    skip: '跳过引导',
    prev: '上一步',
    next: '下一步',
    done: '完成',
    reopen: '新手引导',
    steps: {
      done: {
        title: '一切就绪',
        desc: '你已经了解了核心功能，现在就开始构建你的知识助手吧！随时可点击菜单顶部昵称旁的帮助按钮重新查看引导。'
      },
      models: {
        title: '配置你的模型',
        desc: '这是关键一步：在模型管理中添加对话、向量等模型，知识库与对话功能才能正常工作。点击「添加模型」即可开始配置。'
      },
      settings: {
        title: '账户与设置入口',
        desc: '点开这里可以管理账户、成员与系统设置。需要再次查看本引导时，可点击菜单顶部昵称旁的帮助按钮重新打开。'
      },
      agents: {
        title: '打造专属智能体',
        desc: '把知识库、提示词与工具组合成可复用的智能体，沉淀你的专业能力。'
      },
      chat: {
        title: '发起智能对话',
        desc: '基于知识库内容向 AI 提问，获得带引用来源的精准回答。点击这里开始新对话。'
      },
      knowledge: {
        title: '创建你的知识库',
        desc: '知识库是一切的起点：上传文档、网页或 FAQ，小知会自动解析并建立索引。点击这里进入知识库。'
      },
      welcome: {
        title: '欢迎使用小知',
        desc: '只需几步，带你快速了解知识库、对话与智能体的核心用法。点击「下一步」开始。'
      },
      assistant: {
        title: '认识小知助手',
        desc: '可以问小知的版本、功能和配置，也可以结合当前页面，以你的身份创建智能体、设置定时任务或整理知识。'
      }
    }
  },
  assistantEntryGuide: {
    stepOf: 'v0.9.0 新功能',
    skip: '知道了',
    interactHint: '点击高亮入口，打开助手试试。'
  },
  chatHeader: {
    automationTask: '自动化',
    moreActions: '更多对话操作',
    toggleSandboxPanel: '沙箱终端',
    copyMarkdown: '复制为 Markdown',
    deleteSession: '删除对话',
    renamePlaceholder: '输入对话标题',
    temporaryWorkspace: '临时工作区',
    markdownCopied: '完整对话已复制为 Markdown',
    markdownCopyFailed: '复制 Markdown 失败，请稍后重试',
    clearConfirmTitle: '清空对话消息',
    clearConfirmBody: '确认清空当前对话的全部消息？对话本身会保留，此操作无法恢复。',
    deleteConfirmTitle: '删除对话',
    deleteConfirmBody: '确认删除当前对话？删除后将无法恢复。',
    deleteSuccess: '对话已删除',
    markdown: {
      sessionId: '会话 ID',
      exportedAt: '导出时间',
      user: '用户',
      assistant: '助手',
      attachments: '附件',
      references: '引用'
    },
    grants: {
      menu: '已允许的操作',
      description: '本对话中已允许、不再询问的操作。撤销后再次调用时会重新询问。',
      empty: '暂无已允许的操作',
      revoke: '撤销',
      revoked: '已撤销',
      revokeFailed: '撤销失败',
      loadFailed: '加载失败'
    }
  },
  menu: {
    sessionInProgress: '会话进行中',
    sessionUnread: '有新回复',
    knowledgeBase: '知识库',
    agents: '智能体',
    automations: '自动化',
    artifacts: '产物',
    organizations: '共享空间',
    newChat: '新对话',
    settings: '系统设置',
    logout: '退出登录',
    clearMessages: '清空消息',
    clearMessagesSuccess: '消息已清空',
    clearMessagesFailed: '清空消息失败，请稍后再试',
    renameSession: '修改标题',
    renameSessionSuccess: '标题已更新',
    renameSessionFailed: '修改标题失败，请稍后再试',
    batchManage: '批量管理',
    newSession: '新会话',
    pin: '置顶',
    unpin: '取消置顶',
    pinFailed: '置顶失败，请稍后再试',
    unpinFailed: '取消置顶失败，请稍后再试',
    search: '搜索',
    collapseSidebar: '收起侧边栏',
    expandSidebar: '展开侧边栏',
    myChats: '我的对话',
    apiChats: 'API 会话',
    noSessions: '暂无对话'
  },
  resourceSort: {
    title: '排序',
    updatedTime: '更新时间',
    updatedTimeDescription: '默认选项。',
    createdTime: '创建时间',
    createdTimeDescription: '查看最新或最早创建的内容',
    name: '名称',
    nameDescription: '快速寻找明确知道名称的内容',
    recentlyUpdated: '最近更新',
    earliestUpdated: '最早更新',
    recentlyCreated: '最近创建',
    earliestCreated: '最早创建',
    nameAscending: 'A–Z',
    nameDescending: 'Z–A'
  },
  artifactLibrary: {
    title: '产物',
    subtitle: '智能体在各个会话中生成的文件，都会汇总在这里',
    typeFilter: '按类型筛选',
    searchPlaceholder: '搜索文件名',
    total: '共 {count} 个文件',
    versions: '{count} 个版本',
    preview: '预览',
    delete: '删除',
    deleteTitle: '删除这个文件？',
    deleteConfirm: '将永久删除「{name}」，包括已保存的文件内容，且无法恢复。',
    deleteConfirmVersions: '将永久删除「{name}」的全部 {count} 个版本，包括已保存的文件内容，且无法恢复。',
    deleted: '文件已删除',
    deleteFailed: '删除失败，请稍后重试',
    download: '下载',
    downloadFailed: '下载失败，请稍后重试',
    openSession: '打开所在会话',
    untitledSession: '未命名会话',
    loadMore: '加载更多',
    loadFailed: '产物加载失败',
    retry: '重试',
    clearFilters: '清除筛选',
    noMatches: {
      title: '没有匹配的文件',
      description: '换个关键词或文件类型试试'
    },
    empty: {
      title: '还没有产物',
      description: '在对话中让智能体生成报告、表格或演示文稿，文件会出现在这里'
    },
    groups: {
      today: '今天',
      yesterday: '昨天',
      last7Days: '最近 7 天',
      last30Days: '最近 30 天',
      earlier: '更早'
    },
    categories: {
      all: '全部',
      document: '文档',
      spreadsheet: '表格',
      presentation: '演示文稿',
      image: '图片',
      web: '网页',
      data: '数据'
    }
  },
  localBrowser: {
    pipOpen: '弹出悬浮窗',
    pipReturn: '返回对话小窗',
    pipFailed: '无法打开悬浮窗，请重试。',
    captureScreenshot: '截取网页画面',
    navigationIncomplete: '导航未达到目标加载阶段，请检查当前页面。',
    noEntries: '没有返回记录。',
    stopping: '正在结束任务…',
    elapsedSeconds: '{seconds} 秒',
    searchInstructionsTitle: '浏览器搜索指令',
    searchInstructionsDescription: '设置你偏好的搜索引擎和搜索地址。',
    searchInstructionsHint: '保存后下次请求生效，留空使用默认指令。',
    searchInstructionsReset: '恢复默认',
    searchInstructionsSaved: '已保存',
    sourceHint: '本轮使用本机浏览器查询和操作网页，可与联网搜索、知识库及其他工具配合使用。',
    pressKey: '按键',
    hoverPage: '悬停元素',
    scrollPage: '滚动页面',
    focusElement: '聚焦元素',
    blurElement: '移开焦点',
    selectOption: '选择选项',
    closeTab: '关闭标签页',
    runScript: '执行网页脚本',
    readConsole: '查看控制台',
    readNetwork: '查看网络请求',
    resizeWindow: '调整窗口大小',
    emulateDevice: '模拟设备',
    actionPending: '正在操作浏览器…',
    actionRecorded: '已记录浏览器操作',
    untitledTab: '未命名标签页',
    contentTruncated: '仅显示部分网页内容。',
    controlScope: '仅控制本对话的浏览器操作',
    pauseHint: '中断当前浏览器操作并保留页面，可继续操作；不会停止整段对话。',
    stopHint: '关闭本任务新建的标签页，归还借用的标签页；不会关闭浏览器或撤销配对。',
    openPage: '打开网页',
    switchPage: '切换网页',
    readPage: '查看网页',
    listTabs: '查看标签页',
    clickPage: '点击元素',
    fillPage: '填写内容',
    waitPage: '等待页面',
    openTab: '新建任务标签',
    switchTab: '切换任务标签',
    authorizeTab: '请求标签授权',
    returnTab: '归还标签',
    needHelp: '等待你操作',
    browserAction: '浏览器操作',
    actionFailed: '未完成',
    actionCompleted: '操作已完成',
    commandBusy: '上一条浏览器操作尚未结束，请等待完成后继续。',
    invalidArguments: '浏览器工具参数格式错误或不完整，智能体需要修正后再执行。',
    commandInterrupted: '浏览器操作已中断，请先确认页面状态，再从小预览继续任务。',
    actionFailedHint: '浏览器操作未完成，请检查当前页面后重试。',
    previewStale: '画面暂未更新',
    previewIdle: '已保留最后画面',
    previewLive: '画面同步中',
    previewLoading: '正在获取画面',
    borrowHint: '请切换到要借用的网页，在 BrowserSkill 授权提示中选择「允许」或「拒绝」。授权通过后会自动继续；「继续操作」只恢复暂停的任务，不代替借用授权。',
    helpHint: '点击预览前往浏览器，完成上述步骤后，在浏览器帮助提示中确认完成。',
    settingsTitle: '浏览器连接',
    settingsDescription: '通过 BrowserSkill 连接本机 Chrome 或 Edge，配对后即可在对话中操作真实网页。',
    openSettings: '前往浏览器连接',
    settingsHint: '在工具箱中连接 BrowserSkill，即可在对话里使用本机浏览器。',
    unavailable: '服务端尚未启用本机浏览器，请联系管理员。',
    source: '浏览器来源',
    sandbox: '沙箱浏览器',
    local: '本机浏览器',
    paused: '已暂停',
    connected: '已连接',
    disconnected: '未连接',
    resume: '继续操作',
    pause: '暂停操作',
    start: '开始任务',
    stop: '结束浏览器任务',
    resumeShort: '继续',
    pauseShort: '暂停',
    stopShort: '结束',
    pairHint: '打开扩展的「连接设置 → 远程连接」，粘贴配对链接并确认服务器。链接 5 分钟内有效，仅可使用一次。',
    copyPairing: '复制配对链接',
    copied: '已复制',
    windowHint: '任务在独立的浏览器任务窗口中运行。借用已有标签页需要你的授权。',
    preview: '本机浏览器任务预览',
    waiting: '等待任务页面',
    startHint: '发起浏览器请求后，会创建独立的任务窗口。',
    revoke: '撤销设备授权',
    revokeConfirm: '撤销后需要重新配对，才能继续使用本机浏览器。',
    failed: '操作失败，请重试',
    productDescription: '开源的 Chrome / Edge 扩展，让智能体在你的浏览器里打开网页、读取内容并完成操作。',
    offline: '离线',
    notPaired: '未配对',
    lastSeen: '最近连接',
    readyHint: '已准备就绪。回到对话，直接描述需要浏览器完成的任务。',
    capabilitiesTitle: '智能体可以',
    sidebarStatus: '在侧边栏显示连接状态',
    reconnectHint: '保留授权，等待扩展自动重连。请确认浏览器和 BrowserSkill 扩展已开启。',
    replaceDevice: '更换浏览器',
    installExtension: '安装 BrowserSkill 扩展',
    storeInstall: 'Chrome 应用商店',
    edgeStoreInstall: 'Edge 加载项',
    extensionMinVersion: '需要 BrowserSkill v{version} 及以上版本，支持 Chrome 和 Edge。',
    extensionOutdated: '当前扩展版本 v{current} 过低，请升级到 v{version} 及以上。',
    manualInstall: '手动安装（备用）',
    storeInstallHint: '在 Chrome 应用商店或 Edge 加载项中安装 BrowserSkill，再回到这里配对。',
    installHint: '无法访问商店或商店版本不兼容时，可下载配套扩展并手动安装。',
    downloadExtension: '下载配套扩展',
    officialExtension: '官方扩展（Chrome 应用商店）',
    installGuide: '如何安装下载的扩展包？',
    pairGuide: '如何使用配对链接？',
    pairBrowser: '连接这台浏览器',
    packageUnavailable: '管理员尚未配置扩展下载包，请向管理员获取配套版本。',
    manualCopy: '点击下方输入框复制链接，5 分钟内有效，仅可配对一次。',
    pairingReady: '链接已复制。请在扩展中粘贴，5 分钟内有效，仅可配对一次。',
    copyAgain: '再次复制',
    usageTitle: '使用方式',
    usageStep1Title: '安装扩展',
    usageStep1Text: '下载 ZIP 后解压，在浏览器地址栏输入 chrome://extensions（Edge 为 edge://extensions），开启「开发者模式」，点击「加载已解压的扩展程序」，选择解压后的扩展目录。',
    usageStep2Title: '配对这台浏览器',
    usageStep2Text: '复制配对链接，在扩展的「连接设置 → 远程连接」中粘贴并确认服务器。配对一次，同一空间的各个对话共用。',
    usageStep3Title: '回到对话描述任务',
    usageStep3Text: '在对话输入栏开启「本机浏览器」，再发送网页任务。配对不会自动开启此选项，任务会在独立的任务窗口中运行。',
    usageStep4Title: '通过预览查看和继续',
    usageStep4Text: '对话里会出现小预览，点击可定位到任务标签。中断或重连后任务仍会暂停，请在预览中点继续；借用已有标签页会先请你确认。',
    running: '运行中',
    locateWindow: '定位到浏览器',
    reconnectShort: '等待浏览器重连'
  },
  toolbox: {
    title: '工具箱',
    unavailable: '当前空间暂无可用的工具。'
  },
  automation: {
    conversationNotice: '此会话由自动化任务运行，不能手动发送消息。请在上方处理待审批事项。'
  },
  nativeAgent: {
    executionMode: '运行方式',
    executionSync: '同步',
    executionAsync: '后台异步',
    asyncUnavailable: '后台异步需要已连接的 Agent Protocol 服务；请选择同步运行后保存。',
    asyncOptionsHelp: '后台异步还可配置 update_strategy（interrupt 或 enqueue，默认 interrupt）和 mode（isolated 或 fork，默认 isolated）。fork 为实验功能，会复制父代理对话历史；切回同步前请移除这两个字段。',
    imageModelHelp: '图片使用已配置的视觉模型，或继承支持图片的主模型。',
    skillsHelp: '直接从目录选择指令、资料与脚本。目录登记不代表依赖已安装。',
    runtimeHelp: '可用的运行环境提供 Shell；无 Shell 模式保留会话文件。旧的不可用配置仍可查看。',
    noShell: '会话文件（无 Shell）',
    configTitle: '原生智能体配置',
    subagents: '专业子代理',
    subagentsHelp: '最多声明 20 个专业子代理。模型、指令和访问等级省略时继承；工具/技能省略或 null 时继承，[] 禁用。结构化输出省略/null 时为普通输出。',
    newSubagent: '新子代理',
    inheritParent: '继承父代理',
    childOptions: '工具、技能与策略（JSON）',
    childOptionsHelp: '可选 allowed_tools、selected_skills、access_level、response_format、permissions、interrupt_on。子代理文件规则只接受额外拒绝。',
    addSubagent: '添加子代理',
    advancedConfig: '输出与策略',
    responseFormat: '结构化输出（JSON Schema）',
    responseFormatHelp: '填写 JSON Schema 对象；null 表示普通输出。仅支持本地引用，保存时由服务端校验完整结构。',
    permissions: '文件权限规则（JSON）',
    permissionsHelp: '规则包含 operations（read/write）、绝对路径 paths、mode（allow/deny/interrupt）。仅限制文件工具；沙箱真实执行路径不支持这些规则，平台授权仍是上限。',
    interruptOn: '工具审批（JSON）',
    interruptOnHelp: '工具名映射 true/false 或 allowed_decisions (approve/edit/reject/respond), description。编辑参数由工具自身结构校验；平台强制审批不能关闭。',
    invalidJson: '请输入有效 JSON。',
    interruptTitle: '智能体等待响应',
    responseSchema: '响应结构',
    responseJson: 'JSON 响应',
    submitResponse: '提交响应',
    waitingResponse: '等待处理',
    responseSubmitted: '响应已提交',
    responseFailed: '响应提交失败',
    toolResponse: '作为工具结果返回的文本',
    editAndRun: '修改后执行',
    respondWithoutRun: '返回文本结果',
    structuredResult: '结构化结果'
  }
}
