export default {
  memorySettings: {
    kinds: {
      profile: '個人資料',
      preference: '偏好',
      fact: '事實',
      task: '在辦事項',
      interest: '長期追蹤'
    },
    usage: {
      title: '記憶何時會被使用'
    }
  },
  imagePipeline: {
    smartocr: {
      name: '智能模式',
      description: '先觀察圖片特徵並進行圖片描述，再根據圖片特徵決定是否呼叫 OCR 對圖片進行辨識，以節省模型呼叫次數並提升解析速度。當辨識到圖片為可校正的文件或標籤頁照片時，會在辨識前自動擺正並裁切頁面，以提升 OCR 準確率；若校正失敗則直接使用原圖。',
      ocr: {
        thinking_enabled: {
          label: '文字辨識時開啟思考',
          description: '讓模型在提取文字前先思考。一般情況下不需要開啟思考，開啟之後不僅更慢，還可能造成大模型思考內容過長截斷正文輸出造成任務失敗。請僅在確認有必要的情況下開啟。'
        }
      },
      observation: {
        thinking_enabled: {
          label: '描述時開啟思考',
          description: '讓模型在描述圖片並觀察屬性前先思考。一般情況下不需要開啟思考，開啟之後不僅更慢，還可能造成大模型思考內容過長截斷正文輸出造成任務失敗。請僅在確認有必要的情況下開啟。'
        }
      },
      preprocess: {
        mode: {
          label: '文件預處理',
          description: '預設關閉。啟用後，會在 OCR 前擺正並裁剪頁面，增加處理時間。自動：依觀察結果判斷；總是：對進入 OCR 的圖片都嘗試預處理；忙碌或超限時使用原圖。',
          options: {
            auto: '自動',
            off: '關閉',
            always: '總是'
          }
        }
      },
      note_flow: {
        label: '由觀察結果決定',
        description: '先描述圖片並觀察屬性，由屬性決定是否值得再為它花一次 OCR。屬性顯示頁面需要擺正時，會先擺正並裁掉周圍環境再識別；若該步驟不可用或判定不適用，則直接用原圖，絕不會比不啟用更差。'
      },
      ocr_on_unobserved: {
        label: '圖片屬性觀察失敗時仍執行 OCR',
        description: '當模型未能正確觀察到圖片屬性時，預設仍執行 OCR 兜底，以免漏掉正文文字；關閉則跳過。（採用 4B 等小參數視覺模型，或自定義的圖片解析提示語與系統提示語衝突時，可能造成觀察失敗；8B 及以上模型的失敗概率很低，不建議關閉）'
      }
    },
    default: {
      name: '傳統',
      description: '使用者根據任務需要手動選擇解析動作開關。',
      ocr: {
        thinking_enabled: {
          label: '文字辨識時開啟思考',
          description: '讓模型在提取文字前先思考。一般情況下不需要開啟思考，開啟之後不僅更慢，還可能造成大模型思考內容過長截斷正文輸出造成任務失敗。請僅在確認有必要的情況下開啟。'
        }
      },
      caption: {
        thinking_enabled: {
          label: '圖片描述時開啟思考',
          description: '讓模型在寫描述前先思考。一般情況下不需要開啟思考，開啟之後不僅更慢，還可能造成大模型思考內容過長截斷正文輸出造成任務失敗。請僅在確認有必要的情況下開啟。'
        }
      },
      ocr_enabled: {
        label: '文字辨識',
        description: '提取圖片中出現的文字。'
      },
      caption_enabled: {
        label: '圖片描述',
        description: '讓模型為每張圖片生成一句內容描述，作為圖片的說明文字。'
      },
      note_actions: {
        label: '兩項動作互相獨立',
        description: '兩項各自開關：關掉識別，圖片仍會被描述；關掉描述，文字仍會被識別。只有兩個都關掉時這張圖才不會被處理 —— 所以面板不允許這種組合。'
      }
    },
    errors: {
      noActionEnabled: '至少開啟一個解析動作，否則多模態不會處理任何內容。'
    }
  },
  imageAttr: {
    layout_upright: {
      label: '文字朝向',
      description: '圖中文字是否正立。歪斜或倒置的頁面，值得在 OCR 之前擺正。',
      values: {
        false: {
          label: '非正立',
          description: '文字被旋轉、傾斜拍攝或倒置'
        },
        true: {
          label: '正立',
          description: '文字方向正常'
        }
      }
    },
    layout_margin: {
      label: '版面留白',
      description: '文字內容之外的部分（桌面、背景、空白）佔整張畫面的比例。留白越大，越能在 OCR 之前把頁面裁得更緊。',
      values: {
        large: {
          label: '大片留白',
          description: '有大片非文字區域 —— 桌面、房間，或拍進來的周邊環境'
        },
        small: {
          label: '少量留白',
          description: '邊緣只有一條窄邊'
        },
        none: {
          label: '無留白',
          description: '文字幾乎鋪滿畫面'
        }
      }
    },
    contain_data_visual: {
      label: '資料可視化',
      description: '圖片是否以圖表、曲線、示意圖或資訊圖的方式承載資料；這類圖即使看起來文字很少，也會保留在 OCR 路徑上。',
      values: {
        false: {
          label: '否',
          description: '否 ── 照片、插畫、圖示或裝飾圖'
        },
        true: {
          label: '是',
          description: '是 ── 圖表、曲線或示意圖'
        }
      }
    },
    contain_text: {
      label: '圖中文字量',
      description: '圖片自身承載多少正文文字，決定是否值得為它單獨跑一輪 OCR。',
      values: {
        block: {
          label: '成段正文',
          description: '成段正文 ── 截圖、表格、文件頁面'
        },
        sparse: {
          label: '少量文字',
          description: '只有少量文字 ── 圖示、路牌、單個標籤'
        },
        none: {
          label: '無文字',
          description: '完全沒有文字'
        }
      }
    }
  },
  tenantInvitation: {
    errors: {
      notPending: '邀請已不在待處理狀態。',
      forbidden: '只有被邀請人本人可以接受或拒絕該邀請。',
      notFound: '邀請不存在或已被撤銷。',
      generic: '操作失敗，請稍後重試。'
    },
    myInbox: {
      title: '我的邀請',
      description: '其他空間發給您的加入邀請。接受後您將以對應角色加入對方空間。',
      empty: '沒有待處理的邀請。',
      acceptButton: '接受',
      declineButton: '拒絕',
      acceptSuccess: '已加入 "{tenant}"。',
      declineSuccess: '已拒絕邀請。',
      from: '邀請人',
      tenantLabel: '空間',
      expiresIn: '到期：{date}',
      messageLabel: '留言'
    }
  },
  tenantMember: {
    title: '成員管理',
    loading: '正在載入成員…',
    retry: '重試',
    audit: {
      action: {
        'rbac.member_added': '新增成員',
        'rbac.member_removed': '移除成員',
        'rbac.member_role_changed': '角色變更',
        'rbac.member_left': '成員退出',
        'rbac.access_denied': '存取被拒',
        'rbac.invitation_sent': '發出邀請',
        'rbac.invitation_accepted': '接受邀請',
        'rbac.invitation_declined': '拒絕邀請',
        'rbac.invitation_revoked': '撤銷邀請',
        'rbac.invitation_expired': '邀請過期'
      }
    },
    errors: {
      lastOwner: '無法降級、移除或退出最後一位 Owner，請先把其他成員提升為 Owner。',
      generic: '操作失敗，請稍後重試。'
    },
    leave: {
      confirmTitle: '確認退出當前空間？',
      confirmBody: '退出後您將無法存取當前空間內的所有知識庫和智慧代理。後續可被再次邀請加入。',
      confirm: '退出',
      success: '已退出當前空間'
    },
    role: {
      owner: '所有者',
      admin: '管理員',
      contributor: '編輯',
      viewer: '訪客'
    },
    permissions: {
      title: '角色權限說明',
      desc: '每個角色在當前空間內能做的事情。伺服器端強制執行，UI 控制項僅作展示。'
    }
  },
  userProfile: {
    title: '使用者資訊',
    description: '查看您的帳戶基礎資訊（使用者 ID、使用者名、帳號、註冊時間），並可修改登入密碼',
    changePassword: {
      label: '修改密碼',
      description: '使用當前密碼驗證後設定新密碼。修改成功後所有裝置上的登入狀態將失效，需要重新登入。',
      currentLabel: '當前密碼',
      currentPlaceholder: '請輸入當前密碼',
      currentRequired: '請輸入當前密碼',
      newLabel: '新密碼',
      newPlaceholder: '請輸入新密碼',
      confirmLabel: '確認新密碼',
      confirmPlaceholder: '再次輸入新密碼',
      submit: '更新密碼',
      success: '密碼已更新，請使用新密碼重新登入',
      failed: '修改密碼失敗，請檢查當前密碼是否正確',
      policyFailed: '新密碼須為 8-32 個字符，且同時包含字母和數字',
      sameAsCurrent: '新密碼不能與當前密碼相同',
      oidcOnlyDescription: '您的帳號透過 OIDC 登入開通，尚未設定本地登入密碼。'
    }
  },
  credential: {
    configured: '已設定',
    unconfigured: '未設定',
    configure: '設定',
    update: '更換',
    remove: '移除',
    inputPlaceholder: '請輸入',
    savedToast: '憑據已儲存',
    saveFailed: '儲存憑據失敗',
    removedToast: '憑據已移除',
    removeFailed: '移除憑據失敗',
    confirmRemovePrompt: '確認移除？此操作不可復原',
    confirmRemove: '確認移除'
  },
  integrations: {
    claw: {
      title: 'WeKnora Skill'
    },
    chrome: {
      title: '知識管理助手'
    },
    agentEditor: {
      desc: '將智慧代理發布到 IM 平台或網站，在集成中心統一管理'
    },
    embedOverview: {
      title: '網頁內嵌通路'
    },
    imOverview: {
      title: '已接入的 IM'
    },
    api: {
      title: 'API 集成',
      updateApiKeyScopeFailed: '更新 API Key 失敗'
    },
    tabs: {
      im: 'IM 集成',
      embed: '網頁內嵌',
      api: 'API 集成',
      chrome: 'Chrome 外掛',
      cli: 'CLI',
      claw: 'Claw Skill',
      mcpserver: 'MCP Server'
    },
    mcpserver: {
      title: 'MCP Server',
      tools: {
        list_knowledge_bases: '列出知識庫',
        list_knowledge_basesDesc: '返回端點範圍內的知識庫及其支持的檢索方式',
        search_knowledge: '語義搜尋',
        search_knowledgeDesc: '按自然語言問題在知識庫中檢索相關片段並附來源',
        grep_chunks: '關鍵字/正則搜尋',
        grep_chunksDesc: '對原始切塊做大小寫不敏感的正則比對，適合精確詞、編號、程式碼',
        list_documents: '列出文件',
        list_documentsDesc: '分頁列出某個知識庫下的文件',
        read_document: '閱讀文件',
        read_documentDesc: '按順序讀取文件的元資訊和切塊內容',
        ask: '問答',
        askDesc: '運行端點設定的預設 Agent，返回帶引用的完整回答，支持多輪續聊',
        wiki_search: '搜尋 Wiki',
        wiki_searchDesc: '在知識庫生成的 Wiki 頁面中搜尋',
        wiki_read_page: '讀取 Wiki 頁面',
        wiki_read_pageDesc: '按 slug 讀取一篇 Wiki 頁面',
        wiki_index: '瀏覽 Wiki 目錄',
        wiki_indexDesc: '查看某個知識庫 Wiki 的目錄結構',
        add_document: '新增文件',
        add_documentDesc: '用 Markdown 文字或 URL 向知識庫新增文件',
        update_document: '更新文件',
        update_documentDesc: '取代 Markdown 文件的內容或標題',
        delete_document: '刪除文件',
        delete_documentDesc: '永久刪除文件及其索引資料'
      },
      groups: {
        retrieve: '檢索與閱讀',
        chat: '問答',
        wiki: 'Wiki',
        ingest: '寫入（謹慎開啟）'
      }
    },
    cli: {
      title: 'WeKnora CLI'
    }
  },
  datasource: {
    title: '資料源管理',
    description: '設定外部資料源，自動同步內容到知識庫',
    add: '新增資料源',
    empty: '暫無資料源',
    edit: '編輯',
    delete: '刪除',
    deleteConfirm: '確定刪除該資料源？同步的知識不會被刪除。',
    deleteSuccess: '資料源已刪除',
    deleteFailed: '刪除失敗',
    syncNow: '立即同步',
    syncTriggered: '同步任務已提交',
    syncFailed: '同步觸發失敗',
    pause: '暫停',
    resume: '復原',
    paused: '已暫停',
    resumed: '已復原',
    pauseFailed: '暫停失敗',
    logs: '日誌',
    syncModeLabel: '同步模式',
    parseModeLabel: '解析模式',
    parseModeHint: '飛書雲文檔的解析方式。塊級解析更快並保留文檔內附件；導出解析將文檔導出為 docx 後解析，圖片與文檔的關聯更完整。',
    createTitle: '新增資料源',
    editTitle: '編輯資料源',
    nameLabel: '名稱',
    namePlaceholder: '輸入資料源名稱',
    sectionBasic: '基本資訊',
    testConnection: '測試連結',
    testSuccess: '連結成功',
    testFailed: '連結失敗',
    connected: '已連結',
    connectionFailed: '連結失敗',
    isRequired: '為必填項',
    credentialsLabel: '憑證',
    resourceHint: '選擇要同步的內容空間/資料夾',
    untitled: '無標題',
    resourceLoadFailed: '載入資源清單失敗',
    noResources: '未找到可同步的知識庫空間',
    noResourcesDesc: '應用需要透過群聊獲得知識庫存取權限才能拉取內容',
    noResourcesDesc_notion: '應用需要獲得 Notion 頁面的存取權限才能拉取內容',
    retryLoadResources: '重新載入',
    guideStep1: '在飛書中建立一個群聊，在群設定「群機器人」中新增你的應用',
    guideStep2: '打開知識庫「設定」→「成員設定」→ 新增成員，搜尋該群聊名稱並新增',
    guideStep3: '確保群聊角色至少為「可閱讀」，然後回到這裡點重新載入',
    guideStep1_notion: '在 Notion 中打開你想要同步的頁面或資料庫',
    guideStep2_notion: '點擊右上角的「···」選單，選擇「Connect to」或「Add connections」',
    guideStep3_notion: '搜尋並選擇你的集成應用（Integration），然後回到這裡點重新載入',
    noResourcesDesc_nextcloud: '找不到可存取的資料夾或支援的檔案',
    guideStep1_nextcloud: '登入 Nextcloud，確認帳號有權讀取所選資料夾',
    guideStep2_nextcloud: '在「個人設定 → 安全性 → 裝置與工作階段」中建立應用程式密碼',
    guideStep3_nextcloud: '在此取代憑證，然後重新載入資源',
    noResourcesDesc_seafile: '該權杖能存取的資料庫為空，或全部為加密資料庫（不支持同步）',
    guideStep1_seafile: '登入 Seafile，確認帳號至少擁有一個未加密資料庫的讀取權限',
    guideStep2_seafile: '在「設定 → Web API 權杖」中生成或重新生成權杖',
    guideStep3_seafile: '回到這裡填入新權杖並點重新載入',
    permissionDocLink: '查看飛書知識庫權限設定文件',
    syncScheduleLabel: '同步頻率',
    conflictLabel: '衝突策略',
    syncDeletions: '同步刪除（源端刪除時同步刪除知識庫中的條目）',
    createAndSync: '建立並立即同步',
    createAndSyncSuccess: '資料源建立成功，同步任務已提交',
    createButSyncFailed: '資料源已建立，但觸發同步失敗',
    updateSuccessSyncHint: '資料源更新成功；編輯不會自動觸發同步，如需重新匯入請點擊「同步」。',
    saveFailed: '儲存失敗',
    syncHistory: '同步歷史',
    refreshLogs: '重新整理日誌',
    noLogs: '暫無同步記錄',
    comingSoon: '即將支持',
    docHint: '在以下地址獲取憑證：',
    openDoc: '打開文件',
    prereqBarText: '首次使用？點擊查看飛書應用設定指引',
    prereqBarText_yuque: '首次使用？點擊查看語雀 Token 設定指引',
    prereqStep1Brief_yuque: '建立語雀個人 Token',
    prereqStep1Desc_yuque: '登入語雀 → 個人頭像 → 設定 → Token → 新建 Token',
    prereqStep2Brief_yuque: '為 Token 勾選所需權限',
    prereqStep2Desc_yuque: '至少勾選 repo:read 和 doc:read（讀取知識庫和文件內容）',
    prereqStep3Brief_yuque: '（可選）企業版填寫 Base URL',
    prereqStep3Desc_yuque: '公有雲使用者無需填寫；語雀企業版或私有部署請填寫企業域名',
    prereqStep1Brief_feishu: '建立飛書自建應用',
    prereqStep1Desc_feishu: '登入飛書開放平台 → 建立企業自建應用',
    prereqStep2Brief_feishu: '新增機器人能力',
    prereqStep2Desc_feishu: '開放平台 → 你的應用 → 新增應用能力 → 機器人',
    prereqStep3Brief_feishu: '設定應用權限',
    prereqStep3Desc_feishu: '為應用開通 wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly 權限',
    prereqStep1Brief_lark: '建立 Lark 自建應用',
    prereqStep1Desc_lark: '登入 Lark 開放平台 → 建立企業自建應用',
    prereqStep2Brief_lark: '新增機器人能力',
    prereqStep2Desc_lark: '開放平台 → 你的應用 → 新增應用能力 → 機器人',
    prereqStep3Brief_lark: '設定應用權限',
    prereqStep3Desc_lark: '為應用開通 wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly 權限',
    prereqStep1Brief_feishu_drive: '建立飛書自建應用',
    prereqStep1Desc_feishu_drive: '登入飛書開放平台 → 建立企業自建應用',
    prereqStep2Brief_feishu_drive: '新增機器人能力',
    prereqStep2Desc_feishu_drive: '開放平台 → 你的應用 → 新增應用能力 → 機器人',
    prereqStep3Brief_feishu_drive: '設定應用權限',
    prereqStep3Desc_feishu_drive: '為應用開通 drive:drive:readonly, drive:export:readonly, docx:document:readonly 權限',
    prereqStep1Brief_lark_drive: '建立 Lark 自建應用',
    prereqStep1Desc_lark_drive: '登入 Lark 開放平台 → 建立企業自建應用',
    prereqStep2Brief_lark_drive: '新增機器人能力',
    prereqStep2Desc_lark_drive: '開放平台 → 你的應用 → 新增應用能力 → 機器人',
    prereqStep3Brief_lark_drive: '設定應用權限',
    prereqStep3Desc_lark_drive: '為應用開通 drive:drive:readonly, drive:export:readonly, docx:document:readonly 權限',
    prereqOpenConsole_yuque: '前往語雀 Token 設定',
    yuqueFolderModeLabel: '目錄結構',
    yuqueFolderModeToc: '按語雀目錄分層',
    yuqueFolderModeNone: '平鋪在根目錄',
    yuqueFolderModeHint: '按語雀的目錄層級放置文件。注意：之後在知識庫裡手動調整的目錄，會在該文件下次同步時被覆蓋回語雀的結構。',
    yuqueTOCOnly: '只同步語雀目錄中可見的文件',
    yuqueTOCOnlyHint: '需要先選擇「按語雀目錄分層」。已經同步進知識庫的文件不受影響──語雀中不在目錄裡的文件只是不再新增，不會被刪除。',
    dingtalkIngestLabel: '釘釘攝取範圍',
    dingtalkIncludeUploadedFiles: '攝取知識庫中的上傳檔案（docx / pptx / xlsx / pdf）',
    dingtalkIncludeUploadedFilesHint: '預設關閉。開啟後，所選範圍內的 Word / PowerPoint / Excel / PDF 上傳檔案會被下載並解析入庫，單一檔案上限 64 MiB；這些檔案的正文會計入儲存與向量化成本。關閉時它們只會被跳過，同步日誌會說明開關未開啟，不會刪除知識庫中已有的副本。',
    prereqBarText_dingtalk: '首次使用？點擊查看釘釘應用設定指引',
    prereqStep1Brief_dingtalk: '建立企業內部應用',
    prereqStep1Desc_dingtalk: '在釘釘開放平台建立企業內部應用，並獲取 Client ID 和 Client Secret',
    prereqStep2Brief_dingtalk: '開通知識庫讀取權限',
    prereqStep2Desc_dingtalk: '開通 Wiki.Workspace.Read、Wiki.Node.Read 和 Storage.File.Read',
    prereqStep3Brief_dingtalk: '填寫操作人 Union ID',
    prereqStep3Desc_dingtalk: '填寫有權存取目標知識庫的釘釘使用者 Union ID',
    prereqOpenConsole_dingtalk: '前往釘釘開放平台設定',
    prereqBarText_ima: '首次使用？點擊查看騰訊 IMA OpenAPI 授權指引',
    prereqStep1Brief_ima: '開通 IMA 智慧代理接入',
    prereqStep1Desc_ima: '登入 https://ima.qq.com/agent-interface 並申請 OpenAPI 接入',
    prereqStep2Brief_ima: '獲取 ClientID 與 APIKey',
    prereqStep2Desc_ima: '在智慧代理接入頁複製 ima-openapi-clientid 與 ima-openapi-apikey 兩個憑證',
    prereqStep3Brief_ima: '授權目標知識庫',
    prereqStep3Desc_ima: '在 IMA 用戶端為該憑證授權需要同步的知識庫，未授權的知識庫不會出現在清單中',
    prereqOpenConsole_ima: '前往 IMA OpenAPI 控制台',
    prereqBotBrief: '為應用新增「機器人」能力',
    prereqBotDesc: '開放平台 → 新增應用能力 → 機器人 → 建立版本併發布',
    prereqPermBrief: '開通 API 權限',
    prereqOpenConsole: '前往飛書開放平台設定',
    prereqMemberBrief: '透過群聊新增為知識庫成員',
    prereqMemberDesc: '建立群聊 → 新增應用為群機器人 → 將群聊新增為知識庫成員',
    back: '上一步',
    next: '下一步',
    save: '儲存',
    schedule30min: '每 30 分鐘',
    schedule1h: '每小時',
    schedule6h: '每 6 小時',
    schedule12h: '每 12 小時',
    schedule24h: '每天',
    neverSynced: '未同步',
    justNow: '剛剛',
    minutesAgo: '{n} 分鐘前',
    hoursAgo: '{n} 小時前',
    daysAgo: '{n} 天前',
    syncError: {
      dingtalk_document_failed: '無法讀取釘釘文件，請檢查存取權限後重試同步。',
      dingtalk_document_too_large: '釘釘檔案超過 64 MiB 下載上限，本次已略過，請壓縮或分割後再同步。',
      dingtalk_resource_failed: '釘釘資源不可用，請檢查存取權限和已選資源後重試。',
      deletion_lookup_failed: '刪除前尋找文件失敗，請查看伺服器日誌',
      deletion_failed: '刪除失敗，請查看伺服器日誌',
      ingest_failed: '匯入失敗，請查看伺服器日誌',
      nextcloud_permission_denied: '無權存取該 Nextcloud 檔案，請檢查帳號權限。',
      nextcloud_not_found: 'Nextcloud 檔案在掃描後消失，下次同步將重試。',
      nextcloud_file_too_large: 'Nextcloud 檔案超過 MAX_FILE_SIZE_MB 限制。',
      nextcloud_empty_file: 'Nextcloud 檔案內容為空，已略過。',
      nextcloud_source_changed: 'Nextcloud 檔案在下載過程中發生變更，下次同步將重試。',
      nextcloud_invalid_response: 'Nextcloud 傳回無效或不完整的 WebDAV 回應。',
      nextcloud_ssrf_blocked: 'Nextcloud 請求遭 SSRF 策略封鎖，請檢查 SSRF_WHITELIST。',
      nextcloud_fetch_failed: '從 Nextcloud 取得檔案失敗，下次同步將重試。',
      seafile_permission_denied: '無權存取該 Seafile 檔案，請檢查權杖所屬帳號的資料庫權限。',
      seafile_not_found: 'Seafile 檔案不存在或已被移動，下次同步將重試。',
      seafile_file_too_large: 'Seafile 檔案超過大小限制，請調大 MAX_FILE_SIZE_MB 或縮小該檔案。',
      seafile_empty_file: 'Seafile 檔案內容為空，已跳過。',
      seafile_source_changed: 'Seafile 檔案在獲取過程中發生變化，下次同步將重試。',
      seafile_invalid_response: 'Seafile 回傳了無法解析的回應，請檢查伺服器版本與反向代理設定。',
      seafile_ssrf_blocked: 'Seafile 檔案下載地址被 SSRF 策略攔截，請將 fileserver 網域加入 SSRF_WHITELIST。',
      seafile_fetch_failed: '從 Seafile 獲取檔案失敗，下次同步將重試。'
    },
    resourceType: {
      wikiSpace: '知識庫空間',
      docCategory: '文件標籤',
      book: '語雀知識庫',
      library: 'Seafile 資料庫'
    },
    scheduleHuman: {
      '30min': '每 30 分鐘',
      '1h': '每小時',
      '6h': '每 6 小時',
      '12h': '每 12 小時',
      '24h': '每天'
    },
    confluence: {
      cloudFolderLimitation: 'Confluence Cloud 暫不支持在此列出空間頂層資料夾等容器下的頁面；選擇整個空間仍會同步它們。'
    },
    field: {
      appId: 'App ID',
      appSecret: 'App Secret',
      clientId: 'Client ID',
      clientSecret: 'Client Secret',
      operatorId: '操作人 Union ID',
      operatorIdHint: '用於按該使用者的權限讀取知識庫，可透過釘釘「查詢使用者詳情」介面獲取',
      integrationToken: 'Integration Token',
      apiToken: 'API Token',
      confluenceEdition: 'Confluence 版本',
      confluenceEditionServer: 'Server / Data Center',
      confluenceEditionCloud: 'Cloud',
      confluenceBaseUrl: 'Confluence 地址',
      confluenceUsername: '使用者名或電子信箱',
      confluencePat: 'Server/DC 個人存取權杖（PAT）',
      confluencePatHint: '選填。填寫後使用 Bearer 驗證，無需使用者名稱和密碼。',
      confluencePassword: 'Server/DC 密碼',
      confluenceApiToken: 'Cloud API 權杖',
      imaClientId: 'IMA ClientID',
      imaApiKey: 'IMA APIKey',
      baseUrl: 'Base URL（可選）',
      baseUrlHint: '留空將使用預設公有雲地址；如果是私有部署/企業內網部署，或需要透過反向代理存取，請填寫自定義地址（例如 https://api-proxy.example.com）',
      feedUrls: '訂閱源地址',
      feedUrlsHint: '每行一個 RSS / Atom 訂閱源地址，支持同時填寫多個',
      authHeaders: '自定義請求頭（可選）',
      authHeadersHint: '用於存取私有訂閱源，每行一個，格式為「名稱: 值」，例如 Authorization: Bearer xxxx'
    },
    drive: {
      folderTokenLabel: '雲盤資料夾 Token',
      folderTokenPlaceholder: '輸入 folder_token 或飛書雲盤資料夾連結',
      folderTokenRequired: '請輸入具體資料夾的 folder_token，不支持雲空間根目錄',
      rootNotSupportedHint: '根目錄不分頁且不返回捷徑，請選擇具體資料夾',
      load: '載入',
      shareHint: '需先將該雲盤資料夾分享給應用所在的群，應用才能存取',
      placeholderTitle: '請先載入雲盤資料夾',
      placeholderDesc: '在上方輸入 folder_token（或從飛書雲盤資料夾 URL 複製）並點擊「載入」',
      loadForbiddenHint: '應用無權存取該資料夾。請在飛書雲盤中將該資料夾分享給應用所在的群後再試。',
      loadAuthHint: '應用憑證無效或缺少雲盤權限，請檢查 App ID / App Secret 及 drive:drive:readonly 等權限。',
      loadNotFoundHint: 'folder_token 不存在或已刪除，請確認從飛書雲盤資料夾 URL 複製的 token 正確。'
    },
    connectorDesc: {
      feishu: '同步飛書知識庫中的文件、表格、檔案',
      lark: '同步 Lark 知識庫中的文件、表格、檔案（飛書國際版）',
      feishu_drive: '同步飛書雲盤資料夾中的文件、表格、檔案',
      lark_drive: '同步 Lark 雲盤資料夾中的文件、表格、檔案（飛書國際版）',
      notion: '同步 Notion 中的頁面和資料庫',
      confluence: '將 Confluence 空間和頁面同步為 Markdown',
      yuque: '同步語雀知識庫中的文件',
      dingtalk: '同步釘釘知識庫中的線上文件',
      rss: '同步 RSS / Atom 訂閱源中的文章',
      ima: '同步騰訊 IMA 知識庫中的文件、筆記與檔案（暫不支持 AI 會話與影片解析）',
      gitlab: '同步 GitLab 專案中的檔案',
      nextcloud: '透過 WebDAV 同步 Nextcloud 中的資料夾與檔案',
      seafile: '同步 Seafile 資料庫中的目錄與檔案'
    },
    connector: {
      feishu: '飛書',
      lark: 'Lark（飛書國際版）',
      feishu_drive: '飛書雲盤',
      lark_drive: 'Lark 雲盤',
      notion: 'Notion',
      confluence: 'Confluence',
      yuque: '語雀',
      dingtalk: '釘釘文件',
      rss: 'RSS / Atom 訂閱',
      ima: '騰訊 IMA',
      gitlab: 'GitLab',
      nextcloud: 'Nextcloud',
      seafile: 'Seafile'
    },
    logDetail: {
      startTime: '開始時間',
      endTime: '結束時間',
      failedItems: '失敗文件',
      failedItemsMore: '還有 {n} 個失敗文件未顯示',
      docsFailedSummary: '{n} 個文件同步失敗'
    },
    logSummary: {
      total: '總次數',
      success: '成功',
      failed: '失敗',
      items: '同步條目'
    },
    logMetric: {
      total: '總計',
      skipped: '跳過',
      failed: '失敗'
    },
    logStatus: {
      running: '同步中',
      success: '成功',
      partial: '部分成功',
      failed: '失敗',
      canceled: '已取消'
    },
    step: {
      selectType: '選擇類型',
      credentials: '設定憑證',
      resources: '選擇範圍',
      strategy: '同步策略'
    },
    conflict: {
      overwrite: '覆蓋更新',
      skip: '跳過已存在'
    },
    seafile: {
      baseUrl: 'Seafile 地址',
      apiToken: 'API 權杖',
      apiTokenHint: '在 Seafile「設定 → Web API 權杖」中生成；帳號對所選資料庫有讀取權限即可，權杖不會隨檔案下載請求傳送。',
      singleLibraryOnly: '一個資料源只能同步一個資料庫，請先取消已選資料庫中的內容再改選。',
      selectionRequired: '請至少勾選一個資料庫、目錄或檔案'
    },
    nextcloud: {
      baseUrl: 'Nextcloud 位址',
      baseUrlHint: '填寫安裝位址，如 https://nextcloud.example.com/cloud，不含 /remote.php/dav。私有網路部署請使用現有的 SSRF_WHITELIST 設定。',
      username: '使用者名稱',
      appPassword: '應用程式密碼',
      appPasswordHint: '在「個人設定 → 安全性 → 裝置與工作階段」中建立應用程式密碼，使用產生的使用者名稱與密碼。',
      selectionRequired: '請至少選取一個資料夾或檔案',
      includeExtensions: '包含的副檔名（選填）',
      excludeExtensions: '排除的副檔名（選填）',
      extensionsHint: '以逗號分隔副檔名，如 .pdf, .md。包含項留空表示所有支援的格式，排除項優先。修改篩選條件也會改變刪除核對範圍。'
    },
    gitlab: {
      baseUrl: 'GitLab 地址',
      accessToken: '個人存取權杖',
      projects: 'GitLab 專案',
      projectsHint: '填寫專案 ID 或命名空間路徑（如 group/project），可選指定分支和目錄。',
      project: '專案',
      projectId: '專案 ID',
      projectIdPlaceholder: '例如：12345 或 group/project',
      ref: '分支',
      refPlaceholder: '留空時使用預設分支',
      paths: '同步目錄',
      pathsPlaceholder: '每行一個目錄；留空同步整個專案',
      addProject: '新增專案',
      projectRequired: '請至少新增一個 GitLab 專案'
    },
    status: {
      active: '已連結',
      paused: '已暫停',
      error: '例外'
    },
    syncMode: {
      incremental: '增量同步',
      full: '全量同步'
    },
    parseMode: {
      inherit: '使用伺服器設定',
      blocks: '塊級解析（預設）',
      export: '導出解析（docx）'
    }
  },
  mermaid: {
    diagram: '圖表',
    expand: '全螢幕查看',
    zoomIn: '放大',
    zoomOut: '縮小',
    reset: '重設',
    download: '下載圖片',
    close: '關閉',
    downloading: '下載中...'
  },
  agentEditor: {
    builtinHint: '這是內建智慧代理，名稱和描述不可修改，但可以調整設定參數',
    fileTypes: {
      label: '支持的檔案類型',
      desc: '限制可選擇的檔案類型，留空表示支持所有類型',
      allTypes: '全部類型',
      pdf: 'PDF 文件',
      word: 'Word 文件 (.docx/.doc)',
      textLabel: '文字',
      text: '純文字檔案 (.txt)',
      markdown: 'Markdown 文件',
      csv: '逗號分隔值檔案',
      excel: 'Excel 表格 (.xlsx/.xls)',
      imageLabel: '圖片',
      image: '圖片檔案 (.jpg/.jpeg/.png)'
    },
    fallback: {
      fixed: '固定回覆',
      model: '模型生成'
    },
    faq: {
      title: 'FAQ 優先策略'
    },
    chatParser: {
      label: '聊天附件解析策略',
      desc: '為不同檔案類型指定解析引擎，僅對當前智慧代理的聊天附件生效',
      waitTimeoutLabel: '附件解析等待超時（秒）',
      waitTimeoutDesc: '單輪問答等待附件解析完成的最長時間，超時後未完成的附件會被跳過。大檔案 / 掃描件可調大。0 表示使用全局預設。'
    },
    audioUpload: {
      label: '語音上傳',
      desc: '啟用後使用者可在對話中上傳音訊檔案，系統將使用 ASR 模型自動轉錄為文字',
      asrModel: 'ASR 模型',
      asrModelDesc: '用於音訊轉錄的語音辨識模型，未設定時音訊檔案將以預留位置形式傳遞',
      asrModelPlaceholder: '請選擇 ASR 模型'
    },
    imageUpload: {
      navLabel: '附件上傳',
      sectionTitle: '附件上傳',
      sectionDesc: '設定對話中圖片、文件、音訊等附件的上傳、解析及對應模型',
      label: '圖片上傳',
      desc: '啟用後使用者可在對話中上傳圖片並由 VLM 理解',
      vlmModel: 'VLM 模型',
      vlmModelDesc: '用於圖片分析的視覺語言模型',
      vlmModelPlaceholder: '請選擇 VLM 模型',
      vlmModelRequired: '啟用圖片上傳時必須選擇 VLM 模型',
      imageUnderstandingLabel: '附件圖片理解 / 掃描件 OCR',
      imageUnderstandingDesc: '對圖片型 PDF/PPT 等掃描件，當解析不出文字時用 VLM 進行 OCR 識別。開啟會增加解析耗時，預設關閉。',
      ocrMaxPagesLabel: '掃描件 OCR 最大頁數',
      ocrMaxPagesDesc: '掃描件送入 VLM 做 OCR 的最大頁數，越多覆蓋越全但越慢、越貴。0 表示使用全局預設。',
      useGlobalDefault: '0 = 全局預設',
      storageProvider: '圖片存儲',
      storageProviderDesc: '選擇圖片檔案的存儲引擎，留空則使用系統預設',
      storageProviderPlaceholder: '選擇存儲引擎',
      storageDefault: '系統預設',
      notConfigured: '未設定',
      goStorageSettings: '去存儲設定中設定'
    },
    llmCallTimeout: {
      label: 'LLM 呼叫超時',
      desc: '模型用戶端的請求逾時設定（秒）；串流回應持續輸出時，總時長可能超過此值。',
      hint: '留空或填 0 表示使用預設值（120 秒）',
      placeholder: '輸入秒數，建議範圍 60-1800'
    },
    mcp: {
      label: 'MCP 服務',
      desc: '選擇 Agent 可以呼叫的 MCP 服務',
      selectLabel: '選擇 MCP 服務',
      selectDesc: '選擇要啟用的 MCP 服務',
      selectPlaceholder: '選擇 MCP 服務',
      authWaitTimeout: '授權等待超時（秒）',
      authWaitTimeoutDesc: '對話中觸發 OAuth 授權時，等待你完成授權的最長秒數，超時後自動跳過授權提示（僅對使用 OAuth 的 MCP 服務生效）。',
      authWaitTimeoutPlaceholder: '預設 600 秒',
      accessLevel: '執行權限上限',
      accessLevelDesc: '修改資料的工具（MCP 工具、Wiki 寫入）能否直接執行：唯讀時不提供這類工具，修改前確認時每次先徵求你同意。被標記為需要審批的 MCP 工具始終需要確認。',
      unavailableService: '不可用服務'
    },
    agentType: {
      label: '智慧代理類型',
      desc: '選擇一個預設會自動填充系統提示語、工具清單和推薦的知識庫範圍。',
      defaultNamePattern: '我的{label}',
      kbIncompatibleWarn: '已選的 {count} 個知識庫不適用於當前類型，請手動調整',
      kbMismatch: {
        ragQa: '未啟用 RAG 檢索',
        wikiQa: '未啟用 Wiki',
        hybridRagWiki: '未啟用任何檢索能力',
        dataAnalysis: '需啟用 RAG（不支持 FAQ）',
        quickAnswer: '快速問答模式需啟用 RAG 檢索',
        generic: '不適用於當前類型'
      }
    },
    im: {
      title: 'IM 集成',
      description: '將智慧代理接入即時通訊平台，支持企業微信、飛書、Slack、Telegram、釘釘、Mattermost、微信、QQBot 和雲之家',
      feishu: '飛書',
      lark: 'Lark（飛書國際版）',
      slack: 'Slack',
      telegram: 'Telegram',
      dingtalk: '釘釘',
      mattermost: 'Mattermost',
      wecom: '企業微信',
      wechat: '微信',
      qqbot: 'QQBot',
      yunzhijia: '雲之家',
      addChannel: '新增通路',
      channelsTitle: 'IM 通路',
      disabled: '已停用',
      editChannel: '編輯通路',
      deleteConfirm: '確定刪除該通路？刪除後無法復原。',
      channelName: '通路名稱',
      channelNamePlaceholder: '輸入通路名稱，方便辨識',
      channelNameDefaultHint: '預設為平台名稱，可自行修改；留空儲存時也會使用平台名稱',
      platform: '平台',
      mode: '接入模式',
      outputMode: '輸出模式',
      outputStream: '流式輸出',
      outputFull: '完整輸出',
      callbackUrl: '回呼地址',
      empty: '暫無 IM 通路',
      unnamed: '未命名通路',
      docLink: '查看接入文件',
      wecomConsole: '企業微信管理後台',
      feishuConsole: '飛書開放平台',
      larkConsole: 'Lark 開放平台',
      slackConsole: 'Slack API 控制台',
      telegramConsole: 'Telegram BotFather',
      dingtalkConsole: '釘釘開放平台',
      dingtalkCardTemplateId: '卡片模板 ID（可選）',
      dingtalkCardTemplateIdHint: '在 open-dev.dingtalk.com/fe/card 建立 AI 卡片模板，啟用後支持打字機效果的流式輸出',
      mattermostConsole: 'Mattermost 集成說明',
      qqbotConsole: 'QQ 開放平台',
      qqbotAPIBaseURLHint: '可選，留空則使用預設正式環境 API 地址。',
      qqbotGatewayURLHint: '可選，留空則自動獲取通用 WebSocket 接入點。',
      yunzhijiaConsole: '雲之家開放平台',
      yunzhijiaRobotDoc: '機器人訊息文件',
      yunzhijiaImageDoc: '開發者平台（圖片功能）',
      yunzhijiaModeHint: '支持 Webhook 和 WebSocket；WebSocket 模式無需設定公網回呼地址。',
      yunzhijiaSendMsgUrl: '傳送訊息地址',
      yunzhijiaSendMsgUrlHint: '用於機器人回覆訊息。',
      yunzhijiaSecret: '簽章金鑰（可選）',
      yunzhijiaSecretPlaceholder: '雲之家機器人設定中的 HmacSHA1 簽章金鑰',
      yunzhijiaSecretHint: '設定後，將對傳入的回呼請求進行 HmacSHA1 簽章驗證',
      yunzhijiaAppId: '應用 App ID（圖片下載）',
      yunzhijiaAppIdPlaceholder: '雲之家開放平台應用 App ID',
      yunzhijiaAppSecret: '應用 App Secret（圖片下載）',
      yunzhijiaAppSecretPlaceholder: '雲之家開放平台應用 Secret',
      yunzhijiaAppCredentialHint: '用於獲取 appAccessToken 並下載使用者傳送的圖片檔案。',
      yunzhijiaTimeout: 'HTTP 超時時間（秒）',
      yunzhijiaTimeoutHint: '透過傳送訊息地址回覆的超時時間，預設 10 秒',
      yunzhijiaAllowedHostSuffix: '允許的主機後綴',
      yunzhijiaAllowedHostSuffixHint: '限制傳送訊息地址的目標域名後綴，提升安全性（如 yunzhijia.com）',
      yunzhijiaSendMsgUrlRequired: '請填寫雲之家機器人設定中的傳送訊息地址',
      mattermostModeHint: 'Mattermost 僅支持 Webhook（出站 Webhook + Bot Token）。',
      mattermostPostToMain: '回覆顯示在頻道主時間軸',
      mattermostPostToMainHint: '開啟後 Bot 回覆作為頻道內新帖子；關閉（預設）則作為原訊息的執行緒回覆，主視窗僅顯示「N 條回覆」。',
      modeHint: '推薦使用 WebSocket 方式接入，設定更簡單',
      consoleTip: '前往獲取憑證資訊',
      wecomWSEndpointHint: '可選，私有化部署時填寫自定義 WebSocket 地址，留空則使用預設公有雲地址。內網地址需將域名加入 SSRF_WHITELIST 環境變數',
      wecomAPIBaseURLHint: '可選，私有化部署時填寫自定義 API 地址，留空則使用預設公有雲地址。內網地址需將域名加入 SSRF_WHITELIST 環境變數',
      feishuAPIBaseURLHint: '可選。若伺服器能直連外網則留空；若需透過代理才能存取飛書，填寫反向代理地址（如 nginx，http://host:port）。內網地址需將域名加入 SSRF_WHITELIST 環境變數',
      fileKnowledgeBase: '檔案儲存知識庫',
      fileKnowledgeBasePlaceholder: '選擇知識庫（可選）',
      fileKnowledgeBaseHint: '設定後，使用者傳送的檔案將自動儲存到該知識庫中',
      sessionMode: '會話模式',
      sessionModeUser: '按使用者（預設）',
      sessionModeThread: '按話題',
      sessionModeHint: '使用者模式：每個使用者獨立對話，使用 /clear 開始新對話。話題模式：每個訊息話題獨立對話，同一話題中多人可協作。',
      replyLanguage: '回覆語言',
      replyLanguageDefault: '跟隨系統預設語言',
      replyLanguageHint: '固定該通路的智慧代理回覆語言；留空時使用部署的預設語言。',
      wechatScanBind: '掃碼綁定微信',
      wechatScanning: '請使用微信掃描二維碼',
      wechatBindSuccess: '微信綁定成功',
      wechatRebind: '重新綁定',
      wechatHint: '需要 iOS 微信 8.0.70+ 版本，僅支持單聊訊息',
      wechatQRExpired: '二維碼已過期，請重新獲取',
      wechatBinding: '綁定中...',
      sectionChannel: '通路資訊',
      sectionConnection: '連結設定',
      sectionCredentials: '平台憑證',
      selectPlatform: '選擇平台',
      selectPlatformDesc: '選擇要接入的即時通訊平台',
      enabled: '啟用通路',
      stepBasic: '基本資訊',
      stepConnection: '連結設定',
      stepKnowledge: '檔案存儲',
      stepCredentials: '平台憑證',
      sectionAccess: '接入與輸出',
      sectionSession: '會話設定',
      sectionCallback: '回呼地址',
      sectionKnowledge: '檔案存儲',
      sectionStatus: '運行狀態'
    },
    embed: {
      title: '網頁內嵌'
    },
    tools: {
      thinking: '思考',
      thinkingDesc: '動態和反思性的問題解決思考工具',
      todoWrite: '制定計劃',
      todoWriteDesc: '建立結構化的研究計劃',
      askUser: '向使用者提問',
      askUserDesc: '在缺少關鍵資訊時向使用者提問，並等待回答後繼續',
      searchKnowledge: '檢索知識庫',
      searchKnowledgeDesc: '語義、關鍵字或混合檢索知識庫切塊',
      readDocument: '閱讀文件',
      readDocumentDesc: '讀取文件元資料與切塊內容，支持分頁和文內尋找',
      listDocuments: '瀏覽文件清單',
      listDocumentsDesc: '分頁列出知識庫中的文件',
      queryGraph: '查詢知識圖譜',
      queryGraphDesc: '從知識圖譜中查詢關係',
      dbQuery: '查詢資料庫',
      dbQueryDesc: '查詢資料庫中的資訊',
      dataAnalysis: '資料分析',
      dataAnalysisDesc: '理解資料檔案並進行資料分析',
      dataSchema: '查看資料元資訊',
      dataSchemaDesc: '獲取表格檔案的元資訊',
      requiresKb: '（需要設定知識庫）',
      requiresRagKb: '（需要關聯啟用向量/關鍵字索引的知識庫）',
      requiresWikiKb: '（需要關聯啟用 Wiki 能力的知識庫）',
      wikiSearch: '搜尋 Wiki',
      wikiSearchDesc: '在 Wiki 知識庫中按關鍵字/語義搜尋頁面',
      wikiReadPage: '閱讀 Wiki 頁面',
      wikiReadPageDesc: '讀取指定 Wiki 頁面的完整內容',
      wikiFlagIssue: '標記 Wiki 問題',
      wikiFlagIssueDesc: '標記頁面中存在的事實錯誤或合併衝突問題',
      wikiWritePage: '建立/覆蓋 Wiki',
      wikiWritePageDesc: '建立新頁面或完全覆蓋已有 Wiki 頁面',
      wikiReplaceText: '局部取代 Wiki',
      wikiReplaceTextDesc: '取代 Wiki 頁面中的特定文字',
      wikiRenamePage: '重新命名 Wiki',
      wikiRenamePageDesc: '重新命名 Wiki 頁面並自動更新關聯連結',
      wikiDeletePage: '刪除 Wiki',
      wikiDeletePageDesc: '刪除 Wiki 頁面並自動清理關聯死鏈',
      wikiReadIssue: '查看 Wiki 問題',
      wikiReadIssueDesc: '查看特定 Wiki 頁面的巡檢問題詳情',
      wikiUpdateIssue: '更新 Wiki 問題',
      wikiUpdateIssueDesc: '更新 Wiki 頁面問題的處理狀態',
      webSearch: '網路搜尋',
      webFetch: '網頁抓取',
      groupBase: '基礎',
      groupRag: '知識庫檢索（RAG）',
      groupWikiRead: 'Wiki 讀取',
      groupWikiEdit: 'Wiki 編輯',
      groupWikiIssue: 'Wiki 巡檢',
      groupData: '資料分析',
      writeWarning: '會修改 Wiki 內容',
      dangerTag: '可寫',
      statusNoKb: '當前未關聯任何知識庫',
      kbMetricRag: 'RAG 知識庫',
      kbMetricWiki: 'Wiki 知識庫',
      statusInactive: '有 {count} 個已勾選工具在當前設定下無法生效',
      searchConversations: '回顧歷史對話',
      searchConversationsDesc: '在使用者自己的歷史會話中查找之前聊過的內容',
      groupStored: '已儲存但未提供的工具',
      switchManagedDesc: '由智慧體的其他設定控制，而不是由此列表決定，在此勾選不會啟用它。取消勾選即可移除。',
      unrecognizedDesc: '目前版本不提供此工具，智慧體無法呼叫它。取消勾選即可移除。',
      keptUnknownWarning: '已儲存。以下已儲存的工具在目前版本中不提供，已保留，但智慧體無法呼叫：{names}',
      droppedWarning: '已儲存。以下工具由智慧體的其他設定控制，已從工具列表中移除：{names}',
      effectiveLabel: '最終啟用的工具',
      effectiveDesc: '根據當前設定計算，這是智慧代理儲存後實際能呼叫的工具集合',
      effectiveEmpty: '當前沒有可用工具，智慧代理將退化為純模型問答'
    },
    desc: {
      name: '為智慧代理設定一個易於識別的名稱',
      description: '簡要描述智慧代理的用途和特點',
      systemPrompt: '自定義系統提示語，定義智慧代理的行為和角色',
      promptInheritance: '保持模板原文時將跟隨模板更新；修改後按自定義內容儲存。智慧推論模式下，這裡定義角色和工作要求，工具權限與本輪來源選擇由系統單獨控制。',
      useCustomSystemPrompt: '替換預設人設',
      useCustomSystemPromptDesc: '開啟後此提示詞替換平台預設人設段；工具使用與引用契約仍由平台注入。關閉時作為附加指令附加在預設人設之後。',
      leaveEmptyDefault: '（留空則使用系統預設）',
      contextTemplate: '定義如何將檢索到的內容格式化後傳遞給模型',
      model: '選擇智慧代理使用的大型語言模型',
      temperature: '控制輸出的隨機性，0 最確定，1 最隨機',
      maxTokens: '模型生成回覆的最大 Token 數。選「預設」時為 2048；選「自定義」後按你填的數儲存。',
      maxTokensAgent: '每一輪推論的最大生成 Token（含工具呼叫 JSON）。預設為 24576。選「自訂」後按你填的數儲存。',
      thinking: '啟用模型的擴展思考能力（需要模型支持）',
      queryUnderstandModel: '用於問題理解（改寫與意圖識別）的模型，留空則復用主對話模型',
      rewriteSystemPrompt: '用於問題改寫的系統提示語（留空使用預設）',
      rewriteUserPrompt: '用於問題改寫的使用者提示語模板（留空使用預設）',
      selectTools: '選擇 Agent 可以使用的工具',
      maxIterations: '限制主 Agent 單輪的模型呼叫次數。',
      kbScope: '選擇智慧代理可存取的知識庫範圍',
      fallbackStrategy: '當無法從知識庫找到相關內容時的處理方式',
      fallbackResponse: '當無法回答時返回的固定文字',
      fallbackPrompt: '當無法從知識庫找到答案時，引導模型生成回覆的提示語',
      memoryEnabled: '允許該智慧代理讀取並補充你的長期記憶。關閉後，與它的對話既不會讀取記憶，也不會新增記憶。空間或個人設定關閉時，這裡開啟也不會生效'
    },
    selection: {
      all: '全部',
      selected: '指定',
      disabled: '停用'
    },
    promptNav: {
      ariaLabel: '提示語目錄',
      system: '系統提示語',
      context: '脈絡模板',
      intent: '意圖提示語',
      rewriteSystem: '改寫 · 系統',
      rewriteUser: '改寫 · 使用者',
      fallback: '檢索兜底'
    },
    intentPrompts: {
      title: '意圖提示語',
      sectionDesc: '為不同查詢意圖設定專屬系統提示語；未自定義時使用系統預設模板',
      intentLabel: '意圖',
      promptPlaceholder: '輸入自定義系統提示語...',
      customized: '已自定義',
      empty: '暫無可用的意圖模板'
    },
    placeholders: {
      available: '可用變數：',
      clickToInsert: '（點擊插入）',
      hint: '（點擊插入，或輸入 {\'{{\'} 喚起清單）'
    },
    questionSuggestions: {
      title: '對話問題推薦'
    },
    navGroups: {
      basic: '基礎',
      knowledge: '知識檢索',
      capability: '能力擴展'
    }
  },
  agentStream: {
    saveToKb: {
      emptyContent: '當前回答為空，無法儲存到知識庫',
      editorOpened: '已打開編輯器，請選擇知識庫後儲存'
    },
    copy: {
      emptyContent: '當前回答為空，無法複製',
      success: '已複製到剪貼簿',
      failed: '複製失敗，請手動複製'
    },
    toolStatus: {
      calling: '正在呼叫 {name}...',
      searchKb: '檢索知識庫',
      searchKbFailed: '檢索知識庫失敗',
      searchMixed: '檢索知識庫和網路',
      searchMixedFailed: '檢索失敗',
      webSearch: '網路搜尋',
      webSearchFailed: '網路搜尋失敗',
      grepSearch: '搜尋關鍵字',
      grepSearchFailed: '搜尋關鍵字失敗',
      getDocInfo: '獲取文件資訊',
      getDocInfoFailed: '獲取文件資訊失敗',
      viewDocument: '查看文件',
      thinkingDone: '完成思考',
      thinkingFailed: '思考失敗',
      updateTodos: '更新任務清單',
      updateTodosFailed: '更新任務清單失敗',
      imageAnalyzing: '正在查看圖片內容...',
      imageAnalysisDone: '已查看圖片內容',
      imageAnalysisFailed: '圖片內容查看失敗',
      attachmentParsing: '正在解析附件...',
      attachmentParsingDone: '已解析附件',
      attachmentParsingFailed: '附件解析失敗',
      queryUnderstanding: '正在理解問題...',
      queryUnderstandDone: '已完成問題理解',
      called: '呼叫 {name}',
      calledFailed: '呼叫 {name} 失敗',
      shellExecRunning: '正在執行沙箱命令...'
    },
    mcp: {
      discoverTools: '發現 MCP 工具',
      listServers: '查看 MCP 服務',
      listTools: '查看 MCP 工具',
      searchTools: '搜尋 MCP 工具',
      describeTool: '讀取工具定義',
      callTool: '呼叫 MCP 工具',
      showing: '已顯示 {count} / {total} 項',
      moreAvailable: '還有更多結果',
      empty: '沒有可顯示的項',
      parameters: '參數',
      expand: '展開說明',
      collapse: '收起',
      required: '必填',
      fullSchema: '完整參數定義',
      failed: 'MCP 操作失敗',
      result: '執行結果'
    },
    ragPipeline: {
      searching: '正在檢索知識庫...',
      searchingWithQuery: '正在檢索知識庫：「{query}」',
      searchingWeb: '正在檢索網路...',
      searchingWebWithQuery: '正在檢索網路：「{query}」',
      searchingMixed: '正在檢索知識庫和網路...',
      searchingMixedWithQuery: '正在檢索知識庫和網路：「{query}」',
      searchDone: '檢索完成'
    },
    attachmentParsing: {
      parsedSummary: '已解析 {count} 個附件',
      parsedWithSkipped: '已解析 {parsed} 個附件，{skipped} 個未完成已跳過',
      noneReady: '沒有可用的已解析附件'
    },
    knowledgeChunksList: {
      chunkRange: '已載入 {fetched} / {total} 個切塊',
      page: '第 {page} 頁，每頁 {pageSize} 個',
      offsetRange: '第 {from}–{to} 塊',
      queryMatches: '文件內搜尋「{query}」命中 {count} 處',
      queryNoMatch: '文件內搜尋「{query}」無比對'
    },
    grepResults: {
      chunkHits: '{count} 片段',
      keywordHits: '{count} 次',
      titleMatch: '標題比對',
      faqEntry: 'FAQ 條目'
    },
    search: {
      noResults: '未找到比對的內容',
      candidatesBelowThreshold: '命中 {count} 條候選，相關性不足，未用於回答',
      foundResultsFromFiles: '找到 {count} 個結果，來自 {files} 個檔案',
      foundResults: '找到 {count} 個結果',
      foundMixedResults: '找到 {count} 個結果（{docCount} 篇文件，{webCount} 條網頁）',
      webResults: '找到 {count} 條網頁',
      grepSummary: '找到 {chunks} 個比對片段，來自 {docs} 個文件'
    },
    plan: {
      inProgress: '進行中',
      pending: '待處理',
      completed: '已完成'
    },
    toolSummary: {
      getDocument: '獲取文件：{title}',
      document: '文件',
      listChunks: '查看 {title}',
      listFaqEntry: '查看 FAQ：{question}',
      deepThinking: '深度思考'
    },
    entityLink: {
      kb: '知識庫',
      doc: '文件',
      chunk: '片段'
    },
    citation: {
      notFound: '未找到內容',
      loadFailed: '載入失敗',
      noKbForWiki: '無法識別關聯的知識庫，無法打開 Wiki'
    },
    weknoraDocs: {
      pages: '{count} 篇文件',
      hits: '符合 {count} 個章節',
      empty: '沒有符合的文件',
      outline: '目錄',
      content: '正文',
      truncated: '正文未讀完，可以繼續讀取',
      failed: '讀取失敗',
      openDoc: '在文件站開啟'
    },
    operations: {
      found: '{count} 個可執行操作',
      unavailableCount: '{count} 個目前不可用',
      empty: '沒有符合的操作',
      unavailableHeading: '目前不可用',
      parameters: '參數',
      required: '必填',
      enum: '可選值',
      range: '範圍 {min}–{max}',
      truncated: '結果已截斷',
      emptyResult: '沒有傳回資料',
      failed: '操作失敗',
      meta: '附加資訊',
      risk: {
        read: '唯讀',
        probe: '檢測',
        write: '寫入',
        destructive: '不可恢復'
      },
      names: {
        session: {
          list: '取得對話清單'
        },
        automation: {
          list: '取得自動化列表',
          create: '建立自動化',
          validate_trigger: '檢查執行時間',
          get: '取得自動化詳情',
          update: '更新自動化',
          delete: '刪除自動化',
          pause: '暫停自動化',
          resume: '恢復自動化',
          run_now: '立即執行自動化',
          list_runs: '取得自動化執行記錄'
        },
        skill: {
          list_installed: '取得已安裝技能清單',
          install: '安裝技能',
          get_installed: '取得已安裝技能詳細資訊',
          uninstall: '解除安裝技能',
          set_enabled: '設定技能啟用狀態',
          list: '取得可執行技能清單',
          list_catalog: '取得工作空間技能清單',
          get_catalog: '取得工作空間技能詳細資訊',
          install_catalog: '將目錄技能安裝至沙箱'
        },
        model: {
          list: '取得模型清單',
          list_providers: '取得模型供應商清單',
          get_provider: '取得模型供應商詳細資訊',
          get: '取得模型詳細資訊',
          delete: '刪除模型',
          update: '更新模型顯示資訊',
          copy: '複製模型設定'
        },
        message: {
          chat_history_stats: '取得聊天歷史統計',
          search: '搜尋歷史對話',
          list: '取得訊息歷史'
        },
        mcp_service: {
          list: '取得 MCP 服務清單',
          create: '建立 MCP 服務',
          get: '取得 MCP 服務詳細資訊',
          update: '更新 MCP 服務',
          delete: '刪除 MCP 服務',
          test: '測試 MCP 服務連線',
          list_tools: '即時查詢 MCP 工具',
          get_metadata: '查看已同步 MCP 工具',
          refresh_metadata: '同步 MCP 工具目錄'
        },
        web_search_provider: {
          list: '取得網路搜尋服務列表',
          get: '取得網路搜尋服務詳情',
          list_types: '取得網路搜尋服務類型',
          test: '測試網路搜尋連線',
          update: '修改網路搜尋服務',
          delete: '刪除網路搜尋服務'
        },
        system: {
          get_info: '查詢版本與系統資訊'
        },
        workspace: {
          get: '查詢目前空間資訊',
          update: '修改目前空間基本資訊',
          list_members: '查詢目前空間成員'
        },
        system_admin: {
          list_admins: '查詢系統管理員',
          list_users: '查詢平台使用者',
          list_settings: '查詢系統設定',
          get_queues: '查詢工作佇列執行狀態',
          list_tasks: '查詢佇列工作'
        },
        wiki: {
          list_folders: '取得 Wiki 資料夾清單',
          create_folder: '建立 Wiki 資料夾',
          list_issues: '取得 Wiki 頁面問題清單',
          lint: '檢查 Wiki 頁面',
          move_page: '移動 Wiki 頁面',
          get_page: '取得 Wiki 頁面',
          rebuild_links: '重建 Wiki 連結',
          revert: '還原 Wiki 頁面版本',
          list_revisions: '取得 Wiki 頁面版本清單',
          get_stats: '取得 Wiki 統計資訊'
        },
        knowledge: {
          list: '取得知識清單',
          list_folders: '取得知識資料夾清單',
          rename_folder: '重新命名或移動資料夾',
          create_manual: '手動建立知識',
          create_from_url: '從連結建立知識',
          batch_delete: '批次刪除知識',
          batch_reparse: '批次重新解析知識',
          move_to_folder: '移動知識至資料夾',
          update_manual: '更新手動建立的知識',
          move: '移動知識至其他知識庫',
          get_move_progress: '取得知識移動進度',
          set_tags: '設定知識標籤',
          get: '取得知識詳細資訊',
          update: '更新知識',
          delete: '刪除知識',
          cancel_parse: '取消知識解析',
          reparse: '重新解析知識',
          get_parse_progress: '取得知識解析進度'
        },
        faq: {
          batch_update: '批次修改 FAQ 狀態與標籤',
          list_entries: '取得 FAQ 項目清單',
          delete_entries: '批次刪除 FAQ 項目',
          get_entry: '取得 FAQ 項目詳細資訊',
          update_entry: '更新 FAQ 項目',
          add_similar_questions: '新增相似問題',
          create_entry: '建立 FAQ 項目'
        },
        knowledge_base: {
          list_parser_engines: '取得可用解析引擎',
          copy: '複製知識庫內容',
          duplicate: '複製知識庫設定',
          get_copy_progress: '取得知識庫複製進度',
          list: '取得知識庫清單',
          create: '建立知識庫',
          get: '取得知識庫詳細資訊',
          delete: '刪除知識庫',
          update: '更新知識庫',
          list_activity: '取得知識庫活動記錄',
          search: '搜尋知識庫',
          list_move_targets: '取得可移動的目標知識庫',
          generate_profile: '產生知識庫描述',
          list_tags: '取得知識庫標籤清單',
          create_tag: '建立知識庫標籤',
          update_tag: '更新知識庫標籤',
          delete_tag: '刪除知識庫標籤',
          list_shared: '取得共用知識庫清單'
        },
        chunk: {
          get: '取得分塊詳情',
          update: '更新分塊',
          list_revisions: '取得分塊歷史版本',
          revert: '還原分塊歷史版本',
          list: '取得知識分塊清單'
        },
        artifact: {
          list: '取得產物庫檔案清單'
        },
        agent: {
          list: '取得智慧體清單',
          create: '建立智慧體',
          get: '取得智慧體詳細資訊',
          delete: '刪除智慧體',
          update: '更新智慧體',
          copy: '複製智慧體'
        },
        data_source: {
          list: '取得資料來源清單',
          get: '取得資料來源詳情',
          test: '測試資料來源連線',
          sync: '同步資料來源',
          pause: '暫停資料來源同步',
          resume: '恢復資料來源同步',
          list_sync_logs: '取得資料來源同步紀錄',
          get_sync_log: '取得資料來源同步進度',
          list_resources: '查詢資料來源可同步資源',
          update_sync: '修改資料來源同步設定'
        }
      }
    },
    shellExec: {
      workDir: '目錄',
      exitCode: '退出碼',
      stdout: '標準輸出',
      stderr: '標準錯誤',
      emptyOutput: '無輸出',
      truncated: '輸出已截斷',
      killed: '已超時終止',
      binarySuppressed: '二進位輸出已省略，請將檔案寫入產物目錄後下載'
    },
    sandboxFiles: {
      found: '找到 {count} 個檔案',
      empty: '暫無檔案',
      truncated: '清單已截斷',
      wrote: '已寫入',
      replacements: '取代 {count} 處',
      moreLines: '另有 {count} 行'
    },
    imageView: {
      summary: '已查看「{file}」第 {numbers} 張圖片，共 {total} 張',
      single: '已查看圖片「{file}」',
      descriptionsHeading: '視覺模型的圖片描述',
      imageLabel: '圖片 #{n}',
      noDescription: '未能生成描述',
      remaining: '還有 {count} 張未查看'
    },
    attachmentTarget: {
      list: '全部附件',
      file: '附件',
      images: '{name} 中的圖片',
      imagesUnnamed: '附件中的圖片',
      image: '{name} 第 {n} 張圖片',
      imageUnnamed: '附件第 {n} 張圖片'
    },
    skillFiles: {
      heading: '技能檔案',
      script: '指令碼',
      instructions: '技能說明'
    },
    openPage: {
      open: '開啟',
      retired: '已停用',
      openForm: '開啟並填寫',
      opened: '助手已開啟',
      back: '返回',
      endpoint: '將連線到：',
      draftHint: '已依助手的建議預填。請補上金鑰等憑證，檢查後自行儲存。'
    },
    pageEdit: {
      title: '已填寫 {count} 處',
      undo: '復原',
      undone: '已復原這次填寫',
      undoSkipped: '{count} 處已被你修改或不在頁面上，未復原',
      unsaved: '尚未儲存，請檢查後在頁面上自行儲存'
    },
    pageAccess: {
      viewed: '已查看目前頁面：{location}'
    },
    collaboration: {
      tabs: '任務分頁',
      updates: '{count} 則進展',
      mainConversation: '主對話',
      assignment: '任務說明',
      title: '子任務',
      unnamed: '未命名任務',
      phase: {
        tool_running: '正在使用工具',
        tool_succeeded: '工具已完成',
        tool_failed: '工具失敗'
      },
      status: {
        queued: '排隊中',
        running: '進行中',
        waiting: '等待你處理',
        succeeded: '已完成',
        failed: '失敗',
        interrupted: '已中斷',
        cancelled: '已取消',
        needs_attention: '需要處理',
        cancelling: '正在取消',
        unknown: '狀態未知'
      }
    },
    tools: {
      searchKnowledge: '知識庫檢索',
      grepChunks: '搜尋關鍵字',
      webSearch: '網路搜尋',
      webFetch: '網頁抓取',
      getDocumentInfo: '獲取文件資訊',
      listKnowledgeChunks: '查看知識切塊',
      getRelatedDocuments: '尋找相關文件',
      getDocumentContent: '獲取文件內容',
      wikiReadSourceDoc: '精讀源文件',
      readDocument: '閱讀文件',
      listDocuments: '瀏覽文件清單',
      todoWrite: '計劃管理',
      askUser: '向使用者提問',
      requestSecureForm: '請求登入憑證',
      browserFillSecret: '填寫登入憑證',
      knowledgeGraphExtract: '知識圖譜抽取',
      thinking: '思考',
      attachmentParsing: '解析附件',
      imageAnalysis: '查看圖片內容',
      queryUnderstand: '理解問題',
      queryKnowledgeGraph: '知識圖譜查詢',
      readSkill: '讀取技能',
      executeSkillScript: '執行技能指令碼',
      listSandboxFiles: '列出沙箱檔案',
      readFile: '讀取檔案',
      readSandboxFile: '讀取沙箱檔案',
      writeSandboxFile: '寫入沙箱檔案',
      editSandboxFile: '編輯沙箱檔案',
      shellExec: '執行沙箱命令',
      dataAnalysis: '資料分析',
      dataSchema: '資料結構',
      databaseQuery: '資料庫查詢',
      findOperations: '查找操作',
      runOperation: '執行操作',
      spawn_agent: '啟動智慧體',
      list_agents: '查看智慧體',
      send_message: '傳送訊息',
      followup_task: '繼續任務',
      interrupt_agent: '中斷智慧體',
      wait_agent: '等待智慧體',
      openPage: '開啟頁面',
      viewPage: '查看頁面',
      searchWeKnoraDocs: '搜尋產品文件',
      readWeKnoraDoc: '閱讀產品文件',
      readPage: '查看目前頁面',
      selectTab: '切換標籤',
      fillPage: '填寫頁面'
    },
    mcpOAuth: {
      waiting: '等待授權 · {target}',
      waitingStatus: '等待授權',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '需要授權 {target} 才能繼續',
      titleWithService: 'OAuth 授權 · {service}',
      titleWithTool: 'OAuth 授權 · {service} › {tool}',
      desc: '點擊授權將打開新視窗完成登入，授權成功後會自動繼續本次工具呼叫。',
      authorize: '去授權',
      skip: '跳過',
      countdownShort: '{seconds}s',
      authorizedTag: '已授權',
      timedOutTag: '授權超時',
      canceledTag: '已取消',
      authorizedToast: '授權成功，正在繼續',
      startFailed: '發起授權失敗',
      resumeFailed: '復原執行失敗，請重試',
      skipFailed: '跳過失敗，請重試'
    },
    hostReview: {
      denied: '自動審批已拒絕：{reason}'
    },
    hostApproval: {
      command: '命令',
      grantPath: '需要存取',
      accessWrite: '讀寫',
      accessRead: '唯讀',
      firstAttemptRan: '這條命令已經執行過一次並失敗，批准後會整條重新執行',
      snippet: '攔截詳情',
      sessionRules: '本工作階段允許後，同目錄下這類刪除不再詢問（檔名可以不同）',
      reject: '拒絕',
      approveOnce: '允許一次',
      approveSession: '本工作階段允許',
      approvedOnce: '已允許一次',
      approvedSession: '本工作階段已允許',
      rejectedTag: '已拒絕',
      submitted: '已提交',
      submitFailed: '提交失敗',
      userRejected: '使用者拒絕',
      fileOnly: '只授權這一個檔案',
      writeMode: '方式',
      writeModeOverwrite: '覆寫',
      writeModeAppend: '附加',
      writeModeEdit: '編輯',
      writeBytes: '{bytes} 位元組',
      preview: '內容',
      previewTruncated: '只顯示前 64 KB',
      env: '環境變數',
      skillName: '技能',
      stdin: '標準輸入',
      script: '命令執行的腳本'
    },
    toolApproval: {
      title: '人工審核',
      toolDescription: '工具說明',
      delegatedTask: '子任務',
      waitingStatus: '等待審核',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '允許呼叫 {target}？',
      operationQuestion: '允許{action}「{target}」？',
      operationQuestionNoTarget: '允許{action}？',
      operationTarget: '{action}「{target}」',
      characterCount: '{count} 字',
      argsLabel: '呼叫參數',
      argsModified: '已修改',
      allowInSession: '本會話內同類操作都允許',
      countdownShort: '{seconds}s',
      approve: '透過並執行',
      reject: '拒絕',
      approvedTag: '已透過',
      rejectedTag: '已拒絕',
      parked: '已轉入背景等待，可稍後處理',
      parkedUntil: '已轉入背景等待，{time} 前可處理',
      abandonedTag: '已放棄',
      canceledTag: '已取消',
      invalidJson: '參數不是合法 JSON',
      submitted: '已提交',
      submitFailed: '提交失敗',
      userRejected: '使用者拒絕',
      value: {
        document: '文件',
        faq: '問答',
        wiki: 'Wiki',
        on: '開',
        off: '關',
        vector: '向量',
        keyword: '關鍵詞',
        graph: '圖譜',
        quickAnswer: '快速問答',
        smartReasoning: '智能推理',
        indexSep: '、'
      },
      detail: {
        type: '類型',
        embeddingModel: '嵌入模型',
        summaryModel: '摘要模型',
        captionModel: '圖片描述',
        speechModel: '語音識別',
        storage: '儲存',
        indexes: '索引',
        name: '名稱',
        title: '標題',
        status: '狀態',
        summary: '簡介',
        model: '模型',
        mode: '模式',
        url: '連結',
        from: '從',
        to: '到',
        folder: '目錄',
        page: '頁面',
        version: '版本',
        documents: '文件',
        knowledgeBases: '知識庫',
        mcpServices: 'MCP 服務',
        skills: '技能',
        webSearch: '聯網搜尋',
        multiTurn: '多輪對話',
        transport: '傳輸方式',
        authentication: '認證方式',
        usageInstructions: '使用說明',
        displayName: '顯示名稱',
        enabled: '啟用',
        sandbox: '沙箱',
        sandboxes: '沙箱',
        systemPrompt: '系統提示詞',
        content: '內容',
        kbScope: '知識庫範圍',
        mcpScope: 'MCP 範圍',
        skillsScope: '技能範圍'
      },
      grantLapsed: {
        changed: '先前的允許已失效：自動化的 Agent 設定、成員角色或權限上限已變更。',
        expired: '先前的允許已過期。',
        idle: '先前的允許因長期未使用已失效。'
      }
    },
    promptDock: {
      approvalTitle: '需要你審核',
      oauthTitle: '需要你授權',
      secureFormTitle: '需要你填寫憑據',
      waiting: '等待你處理',
      handle: '去處理',
      pager: '{current} / {total}',
      previous: '上一個',
      next: '下一個',
      collapse: '收起',
      expand: '展開'
    },
    secureForm: {
      onlyFillInto: '只會填入：{domains}',
      observedAt: '瀏覽器目前頁面：{origin}',
      originUnknown: '無法確認瀏覽器目前頁面，請確認瀏覽器停在要登入的網站上再填寫',
      originMismatch: '瀏覽器目前頁面（{origin}）與要登入的網站不一致，請確認後再填寫',
      originInsecure: '瀏覽器目前頁面不是 HTTPS，憑證不會填入',
      savedAccount: '已儲存的帳號',
      useNew: '使用新的帳號密碼',
      username: '帳號',
      password: '密碼',
      saveToVault: '儲存到保險庫',
      useOnce: '僅用一次',
      fill: '填寫',
      decline: '拒絕',
      submittedHidden: '已提交（內容不顯示）',
      declined: '已拒絕',
      timedOut: '逾時未填寫',
      canceled: '已取消',
      submitFailed: '提交失敗',
      savedButClosed: '憑證已儲存到保險庫，但這次請求已結束'
    },
    askUser: {
      answerLabel: '你的回答',
      title: '向你提問',
      selectPlaceholder: '請選擇',
      textPlaceholder: '輸入你的回答',
      otherPlaceholder: '其他（選填）',
      decline: '不回答',
      submit: '提交',
      declinedTag: '已拒絕回答',
      submitted: '已提交',
      answeredTag: '已回答',
      timedOutTag: '逾時未回答',
      canceledTag: '已取消',
      unansweredTag: '未回答',
      submitFailed: '提交失敗'
    }
  },
  kbSettings: {
    parser: {
      title: '解析引擎',
      description: '為不同檔案類型選擇文件解析引擎。未設定的檔案類型將使用內建解析引擎。',
      loading: '載入中...',
      noEngineAvailable: '暫無可用解析引擎，或文件解析服務未設定。',
      default: '預設',
      goConfig: '前往設定 →',
      noEngine: '無可用引擎',
      fileTypePdf: 'PDF 文件',
      fileTypeWord: 'Word 文件',
      fileTypePpt: '簡報',
      fileTypeExcel: 'Excel 表格',
      xlsxFirstRowAsHeader: '將首行作為列標題，並保留在每行脈絡中',
      fileTypeEbook: '電子書',
      fileTypeWebArchive: '網頁歸檔',
      fileTypeCsv: 'CSV 檔案',
      fileTypeText: '純文字',
      fileTypeJson: 'JSON 檔案',
      fileTypeImage: '圖片',
      fileTypeAudiovisual: '音訊',
      engines: {
        opendataloader: {
          name: 'OpenDataLoader',
          desc: 'OpenDataLoader PDF 解析引擎（版面分析，需 Java 11+ 與 opendataloader-pdf）'
        },
        markitdown: {
          name: 'MarkItDown',
          desc: 'Microsoft MarkItDown 文件轉換工具（支持 PDF/Office/HTML 等）'
        },
        paddleocr_vl_cloud: {
          name: 'PaddleOCR-VL Cloud',
          desc: 'PaddleOCR-VL 雲 API'
        },
        paddleocr_vl: {
          name: 'PaddleOCR-VL',
          desc: 'PaddleOCR-VL 自部署服務'
        },
        mineru_cloud: {
          name: 'MinerU Cloud',
          desc: 'MinerU Cloud API'
        },
        mineru: {
          name: 'MinerU',
          desc: 'MinerU 自部署服務'
        },
        anydoc: {
          name: 'anydoc',
          desc: '行程內 Office 文件解析（無需外部服務）'
        },
        simple: {
          name: 'Simple',
          desc: '簡單格式 & 圖片解析（無需外部服務）'
        },
        builtin: {
          name: '內建',
          desc: 'DocReader 內建解析引擎（docx/pdf/xlsx 等複雜格式）'
        }
      }
    },
    storage: {
      title: '存儲引擎',
      selectDescription: '選擇此知識庫綁定的具體存儲實例。',
      defaultTag: '預設',
      instanceLabel: '存儲實例',
      instanceDesc: '同一種存儲類型可以設定多個不同 Endpoint、Bucket 或憑據的實例。',
      migrateHint: '知識庫中已有檔案，需透過存儲遷移流程才能更換實例。',
      manageInstances: '管理存儲實例',
      localStorage: '本地存儲',
      loading: '載入中...'
    },
    vectorStore: {
      title: '向量存儲',
      description: '選擇此知識庫要寫入的向量存儲。綁定不可更改 — 如需將現有 KB 遷移到其他存儲，請建立新 KB 並重新索引。',
      loading: '正在載入向量存儲清單...',
      engineLabel: '向量存儲',
      engineDesc: '從全局向量存儲設定中選擇，或保持系統預設以使用空間的 RETRIEVE_DRIVER 引擎。',
      boundLabel: '已綁定的向量存儲',
      systemDefault: '系統預設',
      immutableHint: '建立後不可更改。如需遷移，請建立一個綁定到目標存儲的新 KB 並重新索引。',
      immutableEdit: '向量存儲綁定在建立後無法更改。',
      unavailableHint: '綁定的向量存儲當前不可用，請在設定 → 向量存儲中檢查其連結設定。',
      goGlobalSettings: '前往向量存儲設定'
    }
  },
  vectorStoreBadge: {
    systemDefault: '系統預設',
    sharedFromOrg: '來自其他組織的共享',
    unknownStore: '未知存儲',
    unavailable: '不可用'
  },
  tools: {
    multiKbSearch: '跨庫搜尋',
    searchKnowledge: '檢索知識庫',
    readDocument: '閱讀文件',
    listDocuments: '瀏覽文件清單',
    knowledgeSearch: '知識庫搜尋',
    grepChunks: '搜尋關鍵字',
    getChunkDetail: '獲取片段詳情',
    listKnowledgeChunks: '查看知識切塊',
    listKnowledgeBases: '列出知識庫',
    getDocumentInfo: '獲取文件資訊',
    queryKnowledgeGraph: '查詢知識圖譜',
    think: '深度思考',
    todoWrite: '制定計劃'
  },
  commandPalette: {
    placeholder: '搜尋知識庫、檔案、對話…',
    clearRecent: '清除',
    retrieval: '檢索參數',
    untitledSession: '未命名對話',
    hotkey: {
      select: '選擇',
      enter: '打開',
      cmdNumber: '直接打開',
      cmdEnter: '發起對話',
      esc: '關閉'
    },
    empty: {
      noResults: '沒有找到比對結果',
      askAi: '直接向 AI 提問',
      adjustRetrieval: '調整檢索參數'
    },
    quick: {
      newChat: '新建對話',
      knowledgeBases: '打開知識庫',
      agents: '打開智慧代理',
      organizations: '打開共享空間',
      settings: '打開設定',
      productTour: '新手引導',
      assistant: '開啟 {name}'
    },
    match: {
      vector: '向量',
      keyword: '關鍵字'
    },
    group: {
      chunks: '知識庫檔案',
      messages: '對話訊息',
      kbs: '知識庫',
      agents: '智慧代理',
      sessionsByTitle: '對話（按標題）',
      commands: '命令',
      recent: '最近搜尋',
      quickActions: '快捷操作'
    },
    scope: {
      placeholder: '在本知識庫中搜尋…',
      remove: '移除範圍篩選（Backspace）'
    }
  },
  assistant: {
    title: '小知助手',
    newConversation: '新對話',
    history: '歷史對話',
    untitledConversation: '未命名對話',
    historyEmpty: '尚無歷史對話',
    historyFailed: '無法載入歷史對話',
    loadMore: '載入更多',
    resize: '調整助手寬度',
    welcomeTitle: '有什麼可以幫你？',
    agentWelcomeDesc: '可以檢查這個智慧代理的設定、調整模型或查看它能檢索的知識庫。',
    welcomeDesc: '我可以解答小知的使用問題，整理知識與文件，幫你設定智慧代理、工具和自動化。',
    startFailed: '啟動助手失敗，請重試',
    chooseAction: '選擇一項功能，或直接輸入你的需求。',
    askAboutAnswer: '就這則回答問 {name}',
    starters: {
      agentConfig: '這個智慧代理的設定有哪些可以改進的地方？',
      agentModel: '這個智慧代理適合換成什麼模型？',
      agentKnowledge: '它能檢索哪些知識庫？',
      wikiIssues: '這篇 Wiki 有哪些內容需要補充或確認？',
      wikiSummary: '這篇 Wiki 的核心內容是什麼？',
      documentSummary: '這篇文件有哪些關鍵結論？',
      recentActivity: '最近上傳或更新了哪些文件？',
      agents: '這些智慧代理分別適合回答什麼問題？',
      messageSources: '這則回答的依據是什麼？',
      messageCheck: '這則回答有沒有說錯？',
      modelCheck: '這個模型的設定適合目前的用途嗎？',
      modelUsage: '哪些智能體和知識庫在用這些模型？',
      mcpTools: '這個 MCP 服務提供哪些工具？',
      mcpCheck: '使用這個服務還需要設定什麼？',
      modelSetup: '我還需要設定哪些模型？',
      mcpSetup: '怎樣接入一個 MCP 服務？',
      releaseHighlights: '目前版本主要更新了哪些內容？',
      gettingStarted: '第一次使用小知，應該先設定什麼？',
      workflow: '知識庫、智慧代理和自動化該怎麼搭配使用？',
      knowledgeOverview: '這些知識庫分別適合查哪些內容？',
      knowledgeType: '文件、FAQ 和 Wiki，我該怎麼選？',
      knowledgeOrganize: '我有一批資料，怎樣整理成好用的知識庫？',
      knowledgeTopics: '這些文件分別在講什麼？',
      knowledgeGaps: '哪些文件解析失敗或還沒完成？',
      faqCoverage: '這些問答涵蓋了哪些常見問題？',
      faqDuplicates: '哪些問答內容重複，可以合併？',
      faqImprove: '哪些答案需要補充或更新？',
      documentSteps: '把這篇文件裡的做法整理成操作步驟',
      documentFaq: '這篇文件可以整理出哪些常見問答？',
      wikiSources: '這篇 Wiki 的結論有哪些來源支持？',
      agentCreate: '怎樣建立一個能查知識庫的智慧代理？',
      agentChoose: '查知識庫時，該用這裡的哪個智慧代理？',
      automationIdeas: '哪些重複工作適合交給自動化？',
      automationCreate: '幫我設一個任務，每週彙整知識庫的更新',
      automationOverview: '我的自動化任務最近執行得怎麼樣？',
      automationSummary: '這個任務最近一次執行產出了什麼？',
      automationSchedule: '這個任務下次什麼時候執行？',
      automationImprove: '這個任務的提示詞和執行安排還能怎麼改進？',
      skillFind: '這裡有哪些技能適合加到智慧代理上？',
      skillAdd: '怎樣將新技能新增並啟用到智慧代理？',
      skillUse: '已新增的技能分別能做什麼？',
      mcpFind: '這些 MCP 服務裡，智慧代理能呼叫哪些工具？',
      mcpExamples: '怎樣讓智慧代理使用這些 MCP 工具？',
      mcpUsage: '這個服務的工具怎麼用？舉個例子',
      modelFit: '這個模型更適合處理哪些任務？',
      modelTypes: '對話、向量和重排模型分別怎麼選？',
      browserConnect: '怎樣將瀏覽器連接給智慧代理使用？',
      browserTasks: '用瀏覽器可以自動完成哪些網頁操作？',
      browserReconnect: '瀏覽器顯示離線時，要怎麼重新連線？',
      messageReuse: '把這個回答整理成可以照著做的步驟',
      chatSummary: '這次對話主要問了什麼、得到了哪些結果？',
      chatCheck: '最後一輪回答有沒有漏掉或說錯的地方？',
      chatFollowup: '基於這次對話，還能接著問哪些問題？',
      artifactRecent: '最近產生了哪些檔案？',
      artifactSources: '這些檔案分別來自哪次對話？',
      artifactCreate: '怎樣讓智慧代理把結果儲存成檔案？',
      organizationShared: '這些共享空間分別共享了哪些知識庫和智慧代理？',
      organizationJoin: '怎樣加入一個既有的共享空間？',
      organizationCreate: '怎樣建立一個共享空間並邀請成員？'
    },
    context: {
      currentPage: '目前頁面',
      detach: '不附帶目前頁面',
      attachedTip: '已附帶目前頁面：{path}',
      detachedTip: '點擊附帶目前頁面：{path}',
      chatMessage: '這則回答',
      pages: {
        knowledge_base: '知識庫',
        wiki: 'Wiki',
        agent_editor: '智能體編輯',
        settings_models: '模型管理',
        mcp_services: 'MCP 服務',
        settings: '設定',
        chat: '對話'
      }
    },
    access: {
      title: '權限等級',
      capped: '空間管理員未開放這一等級',
      levels: {
        auto_write: {
          label: '自動執行',
          desc: '可復原的變更直接執行，刪除仍需確認'
        },
        confirm: {
          label: '變更前確認',
          desc: '每次變更或刪除前都先請你確認'
        },
        read_only: {
          label: '唯讀',
          desc: '只檢視，不做任何變更'
        }
      },
      page: {
        label: '查看和填寫目前頁面',
        desc: '讀取左側頁面，並可代為填寫表單；不會點擊按鈕或儲存'
      }
    },
    fillNotice: {
      title: '助手已填寫 {count} 處',
      undo: '復原',
      dismiss: '關閉'
    },
    bubble: {
      label: '助手快捷操作',
      ask: '問助手',
      polish: '潤飾',
      rewrite: '改寫',
      translate: '翻譯',
      continue: '續寫',
      prompts: {
        polish: '潤飾選取的內容：修正錯字和不通順的地方，不改變原意，直接在原處取代。',
        rewrite: '改寫選取的內容，讓表達更清楚簡潔，直接在原處取代。',
        translate: '翻譯選取的內容：中文譯成英文，其他語言譯成中文，直接在原處取代。',
        continue: '接著選取的內容往下續寫一段，與上下文銜接，寫在選取內容之後。'
      }
    },
    selection: {
      label: '已選取',
      lines: '已選 {count} 行',
      detach: '不帶上選取內容',
      tip: '傳送時會帶上選取的內容：{text}',
      tipField: '傳送時會帶上「{field}」中選取的內容：{text}'
    },
    prompts: {
      createAgent: '請依需求建立智慧體：{request}。先檢查目前可用的模型、知識庫、MCP 與技能，選擇適合的資源；只詢問必要的缺漏資訊，遵循目前權限規則，建立後開啟編輯頁。',
      createAutomation: '請建立排程任務：{request}。未另行指定時使用時區 {timezone}。將說明寫成可獨立執行的完整任務，先驗證時間並顯示後續執行時刻，遵循目前權限規則，不提高執行權限；建立後開啟任務。',
      summarizeActivity: '請只彙整此篩選快照中 loaded_entry_ids 指定的動態：{scope}。依篩選條件查詢並翻頁補齊，說明相關資料、操作者與結果。區分操作紀錄與內文修改，勿將已載入紀錄視為全部動態。',
      explainMcpTools: '請讀取 MCP 服務 {id} 的快取工具目錄，說明功能，提供三個實用提問範例，註明目錄是否過時或不完整。不要重新整理、呼叫工具或修改設定。',
      answerToDocument: '請讀取這則回答與原問題：{source}，整理成清晰文件並保留來源及不確定性。先顯示草稿並讓我選擇目標知識庫，再依目前權限建立文件，不覆寫既有資料。',
      answerToFaq: '請讀取這則回答與原問題：{source}，整理標準問與正確答案。先顯示草稿並讓我選擇目標 FAQ 知識庫，檢查相近項目後依目前權限儲存，不覆寫既有項目。',
      answerToAutomation: '請讀取這則回答與原問題：{source}，將重複工作整理成可獨立執行的排程任務。確認缺漏的頻率、時間與時區，驗證並顯示後續執行時刻，再依目前權限建立，不提高執行權限。',
      writePrompt: '請根據目前智慧代理的用途和設定，幫我草擬系統提示詞。如果目標還不明確，先詢問我。將建議填入目前編輯器，保留範本預留位置，不要儲存或修改已儲存的智慧代理。',
      refinePrompt: '請改善我附帶的系統提示詞，讓職責、回答要求和工具使用規則更清楚，保留原意及範本預留位置。將修改填入目前編輯器，不要儲存或修改已儲存的智慧代理。',
      modelFailure: '請根據目前模型設定和附帶的連線錯誤，分析失敗原因並提供排查步驟。不要讀取或顯示金鑰，也不要修改或儲存設定。',
      mcpFailure: '請根據附帶的工具取得或同步錯誤，檢查 MCP 服務（ID：{id}）並分析原因，提供排查步驟。不要讀取或顯示金鑰，也不要重新連線或修改設定。',
      syncFailure: '請檢查資料來源「{source}」（ID：{id}）的同步記錄（ID：{log}），根據附帶的錯誤範例與失敗數量分析原因。先提供處理建議，不要重試同步或修改資料來源。',
      writeWikiRules: '請根據目前知識庫的用途，為「{field}」起草清楚的規則。如果用途尚不明確，先詢問我。將建議填入對應輸入框，保留系統固定的引用與輸出協定，不要儲存或重新解析。',
      refineWikiRules: '請最佳化附帶的「{field}」規則，讓表達更明確並保留原意。將修改填入對應輸入框，保留系統固定的引用與輸出協定，不要儲存或重新解析。',
      analyzeChunks: '請分析附帶的這次分塊預覽，根據原文與分塊摘錄、當次參數和統計，說明是否有語意割裂、過短或過長的分塊，並提供參數調整建議。區分摘錄可驗證的問題與需要更多原文的判斷，不要修改設定或重建知識庫。'
    },
    actions: {
      summarizeActivity: '彙整這 {count} 筆動態',
      toolExamples: '查看使用範例',
      answerToDocument: '整理為文件',
      answerToFaq: '儲存為 FAQ',
      answerToAutomation: '設為排程任務',
      writePrompt: '幫我寫',
      refinePrompt: '改善提示詞',
      diagnose: '分析原因',
      refineRules: '最佳化規則',
      analyzeChunks: '分析分塊效果'
    },
    create: {
      agentTitle: '用自然語言建立智慧體',
      agentAction: '用助手建立',
      agentHint: '說說它為誰服務、需要完成什麼，助手會協助選擇資源並建立。',
      agentPlaceholder: '例如：建立產品客服智慧體，根據產品知識庫回答使用問題，附上來源，找不到答案時說明原因。',
      automationTitle: '用助手建立任務',
      automationHint: '描述要做什麼、何時執行，助手會幫你整理成自動化任務。',
      automationPlaceholder: '例如：每週五下午 5 點彙整產品知識庫本週更新，列出新增文件與重點變化。',
      requestLabel: '任務描述',
      manual: '手動設定',
      start: '交給助手'
    },
    settingsPages: {
      memory: {
        description: '我可以區分工作區記憶和個人記憶，並說明怎樣讓智慧代理記住空間約定。',
        q1: '工作區記憶和我的個人記憶有什麼不同？',
        q2: '現在啟用了哪些記憶規則？',
        q3: '怎樣讓智慧代理記住這個空間的約定？'
      },
      mymemory: {
        description: '我可以幫你檢視個人記憶、說明它們會用在哪些對話，以及怎樣增刪。',
        q1: '這裡保存了哪些我的個人記憶？',
        q2: '怎樣新增或刪除一條記憶？',
        q3: '這些記憶會用在哪些對話裡？'
      },
      'integration-claw': {
        description: '我可以說明怎樣把小知接到 Claw，以及需要安裝哪個技能。',
        q1: '怎樣把小知接到 Claw？',
        q2: '需要安裝哪個技能？',
        q3: '連上之後能在 Claw 裡做什麼？'
      },
      'integration-chrome': {
        description: '我可以說明瀏覽器擴充功能能做什麼、怎樣安裝登入，以及選取內容會發到哪裡。',
        q1: '瀏覽器擴充功能能做什麼？',
        q2: '怎樣安裝並登入這個擴充功能？',
        q3: '擴充功能裡選取的內容會發到哪裡？'
      },
      'integration-cli': {
        description: '我可以指導你安裝並登入 CLI，並列出常用的知識庫和對話命令。',
        q1: '怎樣安裝並登入 WeKnora CLI？',
        q2: 'CLI 能做哪些知識庫和對話操作？',
        q3: '最常用的幾條命令是什麼？'
      },
      'integration-mcpserver': {
        description: '我可以說明怎樣把小知作為 MCP 服務提供出去，以及會暴露哪些工具。',
        q1: '怎樣把小知作為 MCP 服務提供出去？',
        q2: '外部客戶端要怎樣連線？',
        q3: '這個服務會暴露哪些工具？'
      },
      'integration-api': {
        description: '我可以說明怎樣用 API 發起對話、要帶哪些鑑權，並給出請求範例。',
        q1: '怎樣用 API 發起一次對話？',
        q2: '呼叫時要帶哪些鑑權資訊？',
        q3: '有沒有現成的請求範例？'
      },
      'integration-embed': {
        description: '我可以說明怎樣把對話視窗嵌到網站，以及訪客能用哪些知識庫。',
        q1: '怎樣把對話窗口嵌到自己的網站？',
        q2: '嵌入後訪客能用哪些知識庫或智慧代理？',
        q3: '嵌入程式碼裡要改哪些引數？'
      },
      'integration-im': {
        description: '我可以指導你把飛書、企微等 IM 接到這個空間，並排查收不到訊息的原因。',
        q1: '怎樣把飛書或企微接到這個空間？',
        q2: '接入後使用者要怎樣在 IM 裡用智慧代理？',
        q3: '機器人收不到訊息時要檢查什麼？'
      },
      'system-audit-log': {
        description: '我可以幫你篩選審計記錄、找出高風險操作，並說明日誌保留多久。',
        q1: '最近有哪些高風險操作？',
        q2: '怎樣按人、按空間篩選審計記錄？',
        q3: '這些日誌會保留多久？'
      },
      'platform-api-keys': {
        description: '我可以區分平台 Key 和空間 Key，並說明怎樣建立和作廢。',
        q1: '平台 API Key 和空間 Key 有什麼區別？',
        q2: '怎樣建立一把只能訪問某個空間的 Key？',
        q3: '金鑰外洩後要怎麼立刻作廢？'
      },
      'runtime-queues': {
        description: '我可以幫你檢視任務佇列是否卡住，以及失敗任務怎樣重試。',
        q1: '現在哪些任務佇列卡住了？',
        q2: '解析或索引失敗時要怎麼重試？',
        q3: '怎樣檢視某個佇列裡正在跑的任務？'
      },
      'model-catalog': {
        description: '我可以幫你瀏覽模型目錄、說明怎樣把廠商模型加到空間。',
        q1: '目錄裡有哪些廠商和模型可以接入？',
        q2: '怎樣把目錄裡的模型加到當前空間？',
        q3: '某個廠商還缺什麼配置才能用？'
      },
      'system-global-other': {
        description: '我可以幫你看那些沒有歸類的全域性配置，並說明改動前該注意什麼。',
        q1: '這些未歸類的配置是做什麼的？',
        q2: '改其中某一項會影響什麼？',
        q3: '哪些項不建議在正式環境隨便改？'
      },
      'system-global-security': {
        description: '我可以解釋安全策略、金鑰和會話相關開關，以及改動的風險。',
        q1: '這些安全開關分別保護什麼？',
        q2: '怎樣輪換或作廢平台級金鑰？',
        q3: '哪些安全改動會影響已經登入的使用者？'
      },
      'system-global-runtime': {
        description: '我可以說明執行時、任務和資源相關的全域性選項分別影響什麼。',
        q1: '這些執行時設定會影響哪些後台任務？',
        q2: '怎樣限制並發或逾時？',
        q3: '改完執行時配置何時生效？'
      },
      'system-global-tenant': {
        description: '我可以說明平台上的空間策略、預設配額，以及新建空間時會套用什麼。',
        q1: '新建空間時會套用哪些預設設定？',
        q2: '怎樣限制一個人能建立多少個空間？',
        q3: '空間的預設儲存配額是多少？'
      },
      'system-global-users': {
        description: '我可以幫你檢視平台使用者、說明角色，以及怎樣停用或調整帳號。',
        q1: '平台上現在有哪些使用者？',
        q2: '怎樣停用或調整一個使用者的許可權？',
        q3: '系統管理員和一般使用者差在哪裡？'
      },
      'system-global-access': {
        description: '我可以說明登入、註冊和訪問控制這些全域性開關各自管什麼。',
        q1: '這些訪問控制開關分別限制什麼？',
        q2: '怎樣關閉開放註冊或限制登入方式？',
        q3: '改完這些開關要重啟服務嗎？'
      },
      'system-global': {
        description: '我可以幫你看這套部署的全域性配置、使用者與空間，以及安全相關開關。',
        q1: '這套部署的全域性配置有哪些？',
        q2: '怎樣管理平台上的使用者和空間？',
        q3: '安全相關的開關分別管什麼？'
      },
      system: {
        description: '我可以告訴你當前版本、元件狀態，以及升級前建議核對什麼。',
        q1: '當前版本是什麼，最近更新了哪些內容？',
        q2: '怎樣檢視這次部署的元件狀態？',
        q3: '升級前需要檢查或備份什麼？'
      },
      websearch: {
        description: '我可以幫你看已接入的搜尋服務，並說明怎樣給智慧代理加上連網搜尋。',
        q1: '現在配置了哪些網頁搜尋服務？',
        q2: '怎樣給智慧代理加上連網搜尋？',
        q3: '搜索用的金鑰要填在哪裡？'
      },
      sandbox: {
        description: '我可以說明沙箱用來跑什麼、怎樣加配置，以及指令碼失敗時要檢查哪些項。',
        q1: '沙箱是幹什麼用的？',
        q2: '怎樣新增一套沙箱配置？',
        q3: '智慧代理跑指令碼失敗時，要檢查沙箱的哪些設定？'
      },
      storage: {
        description: '我可以說明檔案存在哪裡、怎樣改到物件儲存，以及配額用完怎麼辦。',
        q1: '上傳的檔案現在存在哪裡？',
        q2: '怎樣改成物件儲存？',
        q3: '儲存配額用完了會怎樣？'
      },
      parser: {
        description: '我可以幫你看預設解析引擎、哪些格式需要換解析器，以及失敗時該查哪裡。',
        q1: '當前預設用哪個檔案解析引擎？',
        q2: '哪些檔案格式需要換解析器？',
        q3: '檔案解析失敗時通常要改哪裡？'
      },
      vectorstore: {
        description: '我可以說明當前向量檢索引擎、換引擎的影響，以及怎樣檢查是否正常。',
        q1: '當前用的是哪套向量檢索引擎？',
        q2: '換引擎會影響已經建好的知識庫嗎？',
        q3: '怎樣檢查檢索引擎是否工作正常？'
      },
      ollama: {
        description: '我可以指導你連線本機 Ollama，並把拉下來的模型加到這個空間。',
        q1: '怎樣連線本機的 Ollama？',
        q2: '連上之後要怎樣把模型加到空間裡？',
        q3: 'Ollama 連不上時通常要檢查什麼？'
      },
      chathistory: {
        description: '我可以說明對話歷史檢索開了沒有、能搜到什麼，以及怎樣建索引。',
        q1: '對話歷史檢索現在開了嗎？',
        q2: '開啟後能搜尋到哪些歷史內容？',
        q3: '怎樣給歷史對話建立索引？'
      },
      members: {
        description: '我可以幫你看成員和角色、說明邀請方式，以及各角色能做什麼。',
        q1: '這個空間現在有哪些成員、分別是什麼角色？',
        q2: '怎樣邀請新成員加入？',
        q3: '管理員和一般成員的權限差在哪裡？'
      },
      tenant: {
        description: '我可以幫你看這個空間的名稱、配額和基本資訊，以及哪些可以改。',
        q1: '這個空間的名稱和儲存配額是多少？',
        q2: '怎樣修改空間名稱或描述？',
        q3: '儲存快用完時會有什麼影響？'
      },
      envvars: {
        description: '我可以說明這些環境變數會用在哪裡，以及個人變數和工作區變數的區別。',
        q1: '這些環境變數會用在哪些技能或智慧代理上？',
        q2: '怎樣安全地填寫我自己的金鑰？',
        q3: '工作區變數和我個人的變數有什麼區別？'
      },
      assistant: {
        description: '我可以說明助手入口、許可權等級，以及它能代你做什麼、不能做什麼。',
        q1: '助手的許可權等級分別意味著什麼？',
        q2: '怎樣把助手入口放到側欄或右下角？',
        q3: '助手能替我改設定或刪除內容嗎？'
      },
      userprofile: {
        description: '我可以幫你檢視和修改帳號資料，並說明登入資訊改動後會發生什麼。',
        q1: '我的帳號信息在哪裡改？',
        q2: '怎樣修改頭像、暱稱或密碼？',
        q3: '改完帳號資訊後需要重新登入嗎？'
      },
      general: {
        description: '我可以幫你看清介面、語言和主題這些個人偏好，以及它們會影響哪些地方。',
        q1: '這些個人偏好分別會影響哪些介面？',
        q2: '語言和主題要怎麼改？',
        q3: '還有哪些個人設定建議先配好？'
      },
      fallback: {
        description: '我可以解釋這個設定頁是做什麼的，改動會影響什麼，以及哪些項建議先配好。',
        q1: '這個設定頁是做什麼的？',
        q2: '改這裡會影響哪些功能？',
        q3: '有哪些項建議先配好？'
      }
    },
    welcomeDescriptions: {
      knowledgeBases: '我可以幫你選擇知識庫類型、整理資料，找到適合目前問題的知識來源。',
      knowledgeBase: '我可以概括這些文件在講什麼，找出最近的更新，以及還沒解析完的文件。',
      document: '我可以提煉文件重點、整理操作步驟，也能把內容轉成常見問答。',
      faq: '我可以檢查問答涵蓋範圍、找出重複問題，幫你把答案寫得更清楚。',
      wiki: '我可以梳理頁面內容、追溯引用來源，幫你找出需要補充或更新的地方。',
      agents: '告訴我想完成什麼，我可以幫你建立智慧代理，搭配模型、知識庫和工具。',
      automation: '我可以把重複工作安排成排程任務，也能檢視執行結果、調整執行計畫。',
      skills: '告訴我任務目標，我可以幫你尋找、新增技能，並設定到合適的智慧代理。',
      mcp: '我可以幫你尋找和接入 MCP 服務，了解可用工具，並設定給智慧代理使用。',
      browser: '我可以引導你連接瀏覽器，了解適合自動操作的任務和所需授權。',
      model: '我可以幫你接入模型、比較用途，檢查設定是否適合目前任務。',
      chat: '我可以概括這次對話做了什麼，核對最後一輪回答，並幫你想好還能接著問什麼。',
      message: '我可以追溯這則回答的來源、核對關鍵資訊，幫你整理成可重複使用的內容。',
      artifacts: '我可以按時間和類型整理這些檔案，找到它們來自哪次對話，以及怎樣讓智慧代理把結果儲存下來。',
      organizations: '我可以幫你看清各共享空間裡有哪些知識庫和智慧代理，以及怎樣建立、加入或邀請成員。'
    },
    help: {
      label: '助手說明',
      title: '小知助手能做什麼',
      identity: '助手以你的身份工作。它能看到和修改的範圍，與你在這個空間裡的角色一致，不會超出你的權限。',
      page: '打開後會附帶目前頁面，可以據此梳理內容、設定智慧代理和自動化，或代為填寫表單。它不會替你點擊按鈕或儲存。',
      access: '輸入框下方可以切換權限：唯讀、修改前確認、自動執行。刪除始終需要你確認。管理員限制的最高等級無法突破。'
    },
    layout: {
      dock: '固定在右側',
      float: '改為懸浮'
    }
  },
  preview: {
    loading: '正在載入文件預覽...',
    loadFailed: '載入文件預覽失敗',
    retry: '重試',
    unsupported: '該檔案類型暫不支持線上預覽',
    unsupportedHint: '請下載檔案後使用本地應用查看',
    zoomIn: '放大',
    zoomOut: '縮小',
    fullscreen: '全螢幕預覽',
    exitFullscreen: '退出全螢幕',
    htmlRendered: '渲染預覽',
    htmlSource: '查看源碼',
    audioNotSupported: '您的瀏覽器不支持音訊播放',
    videoNotSupported: '您的瀏覽器不支持影片播放'
  },
  organization: {
    owner: '建立者',
    roleUpdated: '角色已更新',
    roleUpdateFailed: '更新角色失敗',
    createdByMe: '我建立的',
    joinedByMe: '我加入的',
    share: {
      title: '共享到共享空間',
      selectOrg: '選擇共享空間',
      selectOrgPlaceholder: '請選擇要共享的共享空間',
      permission: '權限',
      permissionTip: '可編輯權限允許成員修改知識庫內容，唯讀權限僅允許檢索和問答',
      shareSuccess: '已共享',
      shareFailed: '共享失敗',
      unshareSuccess: '已取消共享',
      unshareFailed: '取消共享失敗',
      sharedTo: '已共享到',
      noShares: '尚未共享到任何共享空間',
      searchPlaceholder: '搜尋共享空間…',
      loading: '載入中…',
      emptySearch: '未找到比對「{q}」的共享空間',
      addShareDialogTitle: '共享到共享空間',
      unshareAction: '取消共享',
      sharedFrom: '來自',
      permissionReadonly: '唯讀',
      permissionEditable: '可編輯',
      columns: {
        space: '共享空間',
        permission: '權限',
        sharedAt: '共享時間',
        operations: '操作'
      }
    },
    settings: {
      pendingJoinRequestsBadge: '有待審批的加入申請'
    },
    role: {
      admin: '管理員',
      editor: '編輯',
      viewer: '唯讀'
    },
    join: {
      title: '加入共享空間'
    }
  },
  promptTemplate: {
    noTemplates: '暫無模板',
    selectTemplate: '選擇模板',
    useTemplate: '使用模板',
    resetDefault: '復原預設',
    default: '預設',
    withKnowledgeBase: '知識庫',
    withWebSearch: '網路搜尋'
  },
  mcpServiceDialog: {
    addTitle: '新增 MCP 服務',
    addDesc: '連結外部 MCP 服務，智慧代理即可呼叫其中的工具。',
    editTitle: '編輯 MCP 服務',
    basicSection: '基本資訊',
    connectionSection: '連結設定',
    enableServiceDesc: '關閉後該服務不會被呼叫',
    unitSecond: '秒',
    name: '服務名稱',
    namePlaceholder: '請輸入服務名稱',
    transportType: '傳輸類型',
    serviceUrl: '服務 URL',
    serviceUrlPlaceholder: 'https://example.com/mcp',
    enableService: '啟用服務',
    authConfig: '認證設定',
    authType: '認證方式',
    authTypeNone: '無 / 自定義 Header',
    authTypeApiKey: 'API Key / Token',
    authTypeOAuth: 'OAuth 2.0（首次連結授權）',
    oauthScopes: 'Scopes（可選，空格分隔）',
    oauthClientId: 'Client ID（可選）',
    oauthClientIdDesc: '填寫在授權伺服器預先註冊的用戶端；留空則自動進行動態用戶端註冊。更換 Client ID 時請同時更新 Client Secret。',
    oauthClientSecret: 'Client Secret（可選）',
    oauthAuthorization: '授權狀態',
    oauthAuthorized: '已授權',
    oauthRefreshable: 'Token 已過期，將在下次使用時自動重新整理',
    oauthUnauthorized: '未授權',
    oauthAuthorize: '去授權',
    oauthReauthorize: '重新授權',
    oauthRevoke: '撤銷授權',
    oauthAuthorizeHint: '點擊「去授權」會先自動儲存當前設定，再發起授權（每個使用者獨立授權）。',
    apiKeyHeader: '請求頭名稱',
    apiKeyHeaderDesc: '留空預設 X-API-Key。Bearer 方式請填 Authorization，並在下方金鑰值中寫 「Bearer <token>」；需要裸 token 時填 Authorization 並直接填入 token。',
    credentialValue: '金鑰值 / Token',
    optional: '可選',
    advancedConfig: '進階設定',
    timeoutSec: '超時時間(秒)',
    codeImport: {
      toggle: '從程式碼匯入',
      hint: '貼上標準 mcpServers JSON 設定，自動填充表單',
      parse: '解析並填充',
      editOverwriteHint: '匯入會覆蓋當前表單內容（不影響已儲存的憑證，需點儲存生效）',
      toasts: {
        filled: '已填充表單，請檢查後儲存',
        multipleServers: '檢測到多個服務，已匯入第一個：{name}'
      },
      errors: {
        empty: '請先貼上設定內容',
        invalidJson: '無法解析，請檢查 JSON 格式',
        noServer: '未找到 MCP 服務設定',
        missingUrl: '設定缺少 url',
        stdioUnsupported: '暫不支持 stdio（command/args）設定，請使用帶 url 的遠程設定'
      }
    },
    customHeaders: {
      label: '自定義請求頭（可選）',
      desc: '附加到每次 MCP 請求的 HTTP 請求頭，常用於企業閘道鑑權、鏈路追蹤等情境。',
      add: '新增請求頭',
      keyPlaceholder: 'Header 名稱',
      valuePlaceholder: 'Header 值'
    },
    toasts: {
      updated: 'MCP 服務已更新',
      updateFailed: '更新 MCP 服務失敗',
      authorized: '授權成功',
      authorizeFailed: '發起授權失敗',
      revoked: '已撤銷授權',
      revokeFailed: '撤銷失敗'
    },
    rules: {
      nameRequired: '請輸入服務名稱',
      transportRequired: '請選擇傳輸類型',
      urlRequired: '請輸入服務 URL',
      urlInvalid: '請輸入有效的 URL'
    }
  },
  mcpMetadata: {
    searchTools: '搜尋工具名稱或描述',
    retry: '重試',
    details: '詳情',
    description: '描述',
    parameters: '參數',
    required: '必填',
    fullSchema: '完整定義',
    noDescription: '沒有描述',
    noParameters: '沒有參數定義',
    enabled: '啟用工具',
    approval: '呼叫需審批',
    noTools: '沒有比對的工具',
    next: '下一頁',
    policyLoadFailed: '工具策略讀取失敗，請重試後再修改。',
    policySaveFailed: '工具設定儲存失敗',
    tools: 'Tools 清單',
    cacheHint: '尚未同步時會自動連結並儲存完整描述；之後只在重新整理時存取 MCP 服務。',
    fetch: '重新拉取',
    fetching: '正在連結並拉取 Tools…',
    toolCount: '{count} 個工具',
    stale: '連結或認證設定已改變。以下是舊目錄，重新同步後才能供模型使用。',
    notSynced: '尚未同步工具。連結並拉取後，會儲存完整描述和參數定義。',
    syncRequired: '請先連結並拉取 Tools，同步後的目錄才能給模型使用。',
    syncedAt: '同步時間：',
    serverDocumentation: '伺服器端原始說明',
    noServerDocumentation: '該 MCP Server 的 initialize 未返回 instructions / serverInfo.description（均為可選欄位）。工具說明在下方各工具的 description 裡。',
    policyHint: '工具開關與審批設定即時儲存；重新整理目錄不會覆蓋這些設定。',
    columnTool: '工具',
    columnEnabled: '啟用',
    columnApproval: '需審批',
    failed: '工具目錄讀取失敗',
    setupProgress: 'MCP 設定步驟',
    connection: '連結設定',
    toolsAndUsage: '工具與用途說明',
    previous: '上一步',
    usage: '服務用途',
    usageHint: '模型先讀取服務用途，再按需載入具體工具。以下內容由你維護，重新整理不會覆蓋。',
    usageInstructions: '使用說明',
    instructionsPlaceholder: '簡要說明服務用途、適用情境和關鍵使用約束。',
    generateUsage: 'AI 生成',
    generateHint: '根據已同步且啟用的 Tools 生成精簡說明，填入後可編輯，儲存後生效。',
    instructionsRequired: '使用說明不能為空',
    generated: '已生成，請檢查後儲存',
    generateFailed: '生成失敗，請確認 Tools 已同步且已設定可用的對話模型後重試。'
  },
  ollamaSettings: {
    installed: {
      title: '已下載的模型',
      desc: '已安裝在 Ollama 中的模型清單'
    },
    download: {
      title: '下載新模型'
    },
    address: {
      desc: '本地 Ollama 服務的 API 地址，由系統自動檢測。如需修改，請在 .env 設定檔中設定'
    },
    status: {
      desc: '自動檢測本地 Ollama 服務是否可用。如果服務未運行或地址設定錯誤，將顯示"不可用"狀態'
    }
  },
  modelSettings: {
    moreActions: '更多操作',
    title: '模型設定',
    copySuffix: ' 副本',
    builtinTag: '內建',
    confirmDelete: '確定刪除模型「{name}」嗎？',
    debug: {
      reasoningEffort: '思考強度',
      reasoningEffortDesc: '按模型目錄上報的等級傳送 reasoning_effort',
      title: '模型測試',
      description: '使用已儲存的模型設定傳送真實請求；編輯中的修改需儲存後才會生效',
      groupModel: '選擇模型',
      groupInput: '測試輸入',
      groupResult: '運行結果',
      modelType: '模型類型',
      model: '模型',
      modelPlaceholder: '請選擇要測試的模型',
      noModelsForType: '當前類型暫無已新增模型',
      query: '輸入內容',
      queryPlaceholder: '輸入要傳送給模型的內容',
      embeddingInput: '待向量化文字',
      embeddingPlaceholder: '輸入要生成 Embedding 的文字',
      vlmPrompt: '圖片提示語',
      vlmPromptPlaceholder: '例如：請詳細描述這張圖片',
      documents: '候選文件',
      documentsPlaceholder: '每行輸入一個候選文件',
      documentsHint: '每個非空行會作為一個獨立文件傳送給 ReRank 模型',
      imageFile: '圖片檔案',
      similarityMode: '相似度',
      similarityQuery: '查詢文字',
      similarityQueryPlaceholder: '輸入一條查詢，例如：草地上奔跑的狗',
      similarityCandidates: '候選文字',
      similarityCandidatesPlaceholder: '每行輸入一個候選文字',
      similarityHint: '查詢按檢索查詢方式向量化，候選按文件方式向量化，與線上檢索一致；結果按餘弦相似度由高到低排列',
      similarityImage: '候選圖片（可選）',
      similarityImageCandidate: '圖片',
      audioFile: '音訊檔案',
      chooseFile: '選擇檔案',
      parameters: '請求參數',
      systemPrompt: 'System Prompt',
      systemPromptPlaceholder: '可選，輸入系統提示語',
      run: '運行測試',
      copyResult: '複製結果',
      history: '歷史記錄',
      runLabel: '第 {n} 次運行',
      success: '呼叫成功',
      failed: '呼叫失敗',
      rawResponse: '回應內容',
      requestPreview: '請求預覽',
      requestFailed: '模型測試請求失敗',
      metrics: {
        api: '協議',
        thinkingFormat: '思考格式',
        requestedReasoningEffort: '請求思考強度',
        dimension: '向量維度',
        resultCount: '結果數量',
        answerChars: '回答字符數',
        reasoningChars: '推論字符數',
        reasoningReturned: '返回推論內容',
        textChars: '轉寫字符數',
        segmentCount: '分段數量'
      }
    },
    usage: {
      title: '模型無法刪除',
      description: '模型「{name}」仍被以下設定引用。請先打開對應設定並更換模型，再重新刪除。',
      knowledgeBases: '知識庫（{count}）',
      agents: '智慧代理（{count}）',
      openConfiguration: '打開設定',
      truncated: '僅顯示前 {shown} 個，共 {total} 個',
      longTermMemory: '長期記憶'
    },
    builtinModels: {
      title: '內建模型',
      description: '內建模型對所有空間可見，敏感資訊會被隱藏，且不可編輯或刪除。',
      descriptionAdmin: '內建模型對所有空間可見。系統管理員可編輯設定和憑據；刪除仍由部署設定管理。',
      viewGuide: '查看內建模型管理指南'
    },
    toasts: {
      nameRequired: '模型名稱不能為空',
      nameTooLong: '模型名稱不能超過100個字符',
      displayNameTooLong: '顯示名稱不能超過100個字符',
      baseUrlRequired: 'Remote API 類型必須填寫 Base URL',
      baseUrlInvalid: 'Base URL 格式不正確，請輸入有效的 URL',
      dimensionInvalid: 'Embedding 模型必須填寫有效的向量維度（128-4096）',
      updated: '模型已更新',
      added: '模型已新增',
      saveFailed: '儲存模型失敗',
      deleted: '模型已刪除',
      deleteFailed: '刪除模型失敗',
      builtinCannotEdit: '內建模型不能編輯',
      linkedModelMissing: '找不到助手連結的模型，它可能已被刪除',
      builtinCannotDelete: '內建模型不能刪除',
      builtinCannotCopy: '內建模型不能複製',
      copied: '模型已複製',
      copyFailed: '複製模型失敗'
    },
    asr: {
      title: 'ASR 語音模型',
      desc: '設定用於語音辨識和音訊轉錄的語音轉文字模型（如 OpenAI Whisper）',
      empty: '暫無 ASR 語音模型'
    },
    vllm: {
      title: 'VLLM 視覺模型',
      desc: '設定用於視覺理解和多模態的視覺語言模型',
      empty: '暫無 VLLM 視覺模型'
    },
    rerank: {
      title: 'ReRank 模型',
      desc: '設定用於結果重排序的模型',
      empty: '暫無 ReRank 模型'
    },
    embedding: {
      title: 'Embedding 模型',
      desc: '設定用於文字向量化的內嵌模型',
      empty: '暫無 Embedding 模型'
    },
    chat: {
      title: '對話模型',
      desc: '設定用於對話的大型語言模型',
      empty: '暫無對話模型'
    },
    source: {
      remote: 'Remote',
      openaiCompatible: 'OpenAI相容',
      custom: '自定義'
    },
    actions: {
      addModel: '新增模型',
      debugModel: '模型測試'
    },
    typeShort: {
      chat: '對話',
      embedding: 'Embedding',
      rerank: 'ReRank',
      vllm: '視覺',
      asr: '語音'
    }
  },
  mcpSettings: {
    addUsageInstructions: '新增使用說明',
    noUsageInstructions: '尚未填寫使用說明',
    title: 'MCP 服務管理',
    description: '管理外部 MCP (Model Context Protocol) 服務，在 Agent 模式下呼叫外部工具和資源',
    enabled: '已啟用',
    disabled: '已停用',
    addService: '新增服務',
    empty: '暫無 MCP 服務',
    deleteConfirmBody: '確定要刪除 MCP 服務"{name}"嗎？此操作無法復原。',
    unnamed: '未命名',
    builtin: '內建',
    toolCount: '{count} 個工具',
    toolsNotSynced: '尚未同步工具',
    toolsStale: '需重新同步',
    toasts: {
      loadFailed: '載入 MCP 服務清單失敗',
      enabled: '已啟用 MCP 服務',
      disabled: '已停用 MCP 服務',
      updateStateFailed: '更新 MCP 服務狀態失敗',
      linkedServiceMissing: '找不到助手連結的 MCP 服務，它可能已被刪除',
      deleted: 'MCP 服務已刪除',
      deleteFailed: '刪除 MCP 服務失敗'
    }
  },
  conversationSettings: {
    maxTokens: {
      desc: '生成回答的最大Token數量'
    },
    temperature: {
      desc: '控制模型輸出的隨機性，0最確定，1最隨機'
    },
    systemPrompt: {
      desc: '用於普通模式對話的系統級Prompt'
    },
    contextTemplate: {
      desc: '用於普通模式下基於檢索結果生成回答的Prompt模板'
    },
    rerankModel: {
      desc: '用於搜尋結果重排序的模型（可選）'
    },
    chatModel: {
      desc: '用於總結和摘要的大型語言模型'
    },
    rewritePrompt: {
      desc: '控制問題改寫的系統提示語'
    },
    fallbackPrompt: {
      desc: '當選擇模型兜底時使用的提示模板'
    },
    fallbackResponse: {
      desc: '當兜底策略為固定回覆時返回的文字'
    },
    fallbackStrategy: {
      desc: '檢索無結果時採用的處理方式'
    },
    enableQueryExpansion: {
      desc: '召回不足時呼叫大型語言模型生成擴展查詢（增加時延與成本）'
    },
    enableRewrite: {
      desc: '多輪對話自動改寫問題以獲得更優召回'
    },
    rerankThreshold: {
      desc: '重排序階段的最低得分閾值'
    },
    rerankTopK: {
      desc: '重排序後進入答案生成的文件數量'
    },
    vectorThreshold: {
      desc: '向量召回的最低相似度閾值'
    },
    keywordThreshold: {
      desc: '關鍵字檢索的最低得分閾值'
    },
    embeddingTopK: {
      desc: '向量召回階段保留的文件數量'
    },
    maxRounds: {
      desc: '用於多輪脈絡和問題改寫的歷史輪數'
    },
    models: {
      chatGroupLabel: '思考 / 對話模型'
    }
  },
  agentSettings: {
    systemPrompt: {
      desc: '設定 Agent 的系統提示語，支持預留位置模板。預留位置會在運行時自動取代為實際內容。'
    },
    allowedTools: {
      desc: '當前 Agent 可使用的工具清單'
    },
    temperature: {
      desc: '控制模型輸出的隨機性，0 最確定，1 最隨機'
    },
    rerankModel: {
      desc: '搜尋結果重排序，統一不同來源的相關度分數'
    },
    thinkingModel: {
      desc: '用於 Agent 推論和規劃的 LLM 模型'
    },
    maxIterations: {
      desc: '限制 Agent 單次任務的推論步數。選「不限制」時會一直跑到模型自然結束或你手動停止。'
    },
    modelRecommendation: {
      title: '模型推薦'
    }
  },
  uploadTasks: {
    panelLabel: '上傳任務',
    titleUploading: '正在上傳 {done}/{total}',
    titleParsing: '正在解析 {done}/{total}',
    titleDone: '全部完成',
    titleDoneWithIssues: '{ok} 個完成，{bad} 個未成功',
    titleCancelled: '上傳已取消',
    destination: '上傳至「{name}」',
    destinationMany: '上傳至 {count} 個知識庫',
    remaining: '剩餘約 {time}',
    hintUploading: '上傳完成前請不要關閉或重新整理頁面',
    hintParsing: '檔案已全部上傳，解析在後台繼續，可以放心離開此頁面',
    filterAll: '全部',
    filterIssues: '未成功',
    phaseWaiting: '等待上傳',
    phaseSaving: '正在儲存…',
    phasePending: '排隊解析',
    phaseReady: '已完成',
    phaseParseFailed: '解析失敗',
    phaseDuplicate: '知識庫中已有相同檔案',
    phaseCancelled: '已取消',
    cancel: '取消',
    cancelAll: '全部取消',
    retry: '重試',
    retryFailed: '重試 {count} 個',
    open: '查看',
    collapse: '收起',
    expand: '展開',
    close: '關閉',
    closeConfirm: '關閉後將取消剩餘 {count} 個檔案的上傳',
    closeConfirmOk: '取消上傳',
    closeConfirmKeep: '繼續上傳',
    legend: {
      ready: '可檢索',
      active: '處理中',
      waiting: '等待中',
      failed: '失敗',
      duplicate: '已存在'
    },
    eta: {
      seconds: '{n} 秒',
      minutes: '{n} 分鐘',
      hours: '{n} 小時'
    }
  },
  upload: {
    uploadDocument: '上傳文件',
    uploadFolder: '上傳資料夾',
    onlineEdit: '線上編輯',
    deleteRecord: '刪除記錄'
  },
  time: {
    today: '今天',
    yesterday: '昨天',
    last7Days: '近7天',
    last30Days: '近30天',
    lastYear: '近1年',
    earlier: '更早',
    pinned: '已置頂'
  },
  platform: {
    multimodalParsing: '多模態文件解析',
    hybridSearchEngine: '混合檢索 + 知識圖譜',
    ragQandA: 'ReAct 智慧代理問答',
    independentTenant: '獨立空間',
    fullApiAccess: '完整 API 存取',
    knowledgeBaseManagement: '知識庫管理',
    loginShowcase: {
      carouselLabel: '任我行知識庫功能示意',
      switchLabel: '切換功能主題',
      pause: '暫停輪播與流光',
      play: '播放輪播與流光',
      reducedMotion: '已依減少動態效果設定停止自動播放',
      labels: {
        query: '自然語言提問',
        sourceHit: '命中原文',
        citedAnswer: '回答附有引用',
        sourceMaterial: '來源資料',
        productKnowledge: '產品知識',
        delivery: '實施交付',
        customerService: '客戶服務',
        documents: '文件資料',
        webContent: '網頁內容',
        existingKnowledge: '既有知識',
        knowledgeEntry: '統一知識入口',
        materialsReceived: '資料已匯聚',
        contentChange: '內容變化',
        knowledgeReview: '知識審核',
        knowledgeUpdate: '知識更新',
        updateConfirmed: '本次更新已確認'
      },
      themes: {
        review: {
          title: '知識變化，即時更新',
          description: '經過知識審核，讓資料持續產生價值',
          summary: '內容變更先經過審核確認，再進入知識庫更新對應內容。',
          mobile: '內容變化 → 知識審核 → 知識更新',
          tab: '審核更新'
        },
        intake: {
          title: '企業資料，一處匯聚',
          description: '連接文件、網頁與現有知識平台',
          summary: '文件、網頁和既有知識匯入同一個知識入口，資料接收後確認匯聚。',
          mobile: '文件 / 網頁 / 既有知識 → 統一入口',
          tab: '資料匯聚'
        },
        organization: {
          title: '分散文件，有序關聯',
          description: '按主題展開資料，連接相關的知識',
          summary: '來源資料依序展開為產品知識、實施交付和客戶服務三個主題。',
          mobile: '來源資料 → 產品 / 實施 / 服務知識',
          tab: '知識組織'
        },
        query: {
          title: '每次提問，都有依據',
          description: '從自然語言提問，直達有出處的回答',
          summary: '問題進入檢索，命中原文，回答與引用同時顯現。',
          mobile: '提問 → 命中原文 → 回答附有引用',
          tab: '問答溯源'
        }
      }
    }
  },
  font: {
    uiFont: '界面字型',
    uiFontDescription: '用於選單、正文、按鈕等界面大部分文字的字型',
    monoFont: '程式碼字型',
    monoFontDescription: '用於程式碼塊、終端命令、API 金鑰、檔案路徑等技術內容，每個字符等寬顯示，避免 0/O、1/l 混淆',
    selectFont: '選擇字型',
    sansPreview: '示例 Sample 字型 Font — Aa Gg Oo 0123',
    monoPreview: 'const msg = \'Hello\'; // 0O1l',
    fontSize: '字型大小',
    fontSizeDescription: '整體縮放界面（文字、圖示、間距等），切換後立即生效',
    size: {
      small: '小',
      normal: '正常',
      large: '大'
    },
    mono: {
      system: '系統預設',
      menlo: 'Menlo',
      monaco: 'Monaco',
      consolas: 'Consolas',
      cascadia: 'Cascadia Code',
      'dejavu-mono': 'DejaVu Sans Mono',
      'liberation-mono': 'Liberation Mono',
      monospace: '通用等寬'
    },
    sans: {
      system: '系統預設',
      pingfang: '蘋方 PingFang SC',
      georgia: 'Georgia 襯線',
      yahei: '微軟雅黑 Microsoft YaHei',
      times: 'Times New Roman 襯線',
      'noto-cjk': 'Noto Sans CJK',
      'dejavu-serif': 'DejaVu Serif 襯線',
      'sans-serif': '通用無襯線'
    }
  },
  theme: {
    theme: '主題模式',
    themeDescription: '選擇界面的顯示主題，支持跟隨系統自動切換',
    light: '淺色',
    dark: '深色',
    system: '跟隨系統',
    selectTheme: '選擇主題'
  },
  general: {
    title: '常規設定',
    personalSettings: '個人設定',
    description: '設定語言、外觀等基礎選項',
    close: '關閉設定'
  },
  language: {
    zhCN: '簡體中文',
    zhTW: '繁體中文',
    enUS: 'English',
    ruRU: 'Русский',
    koKR: '한국어',
    jaJP: '日本語',
    selectLanguage: '選擇語言',
    language: '語言',
    languageDescription: '選擇界面顯示語言',
    languageSaved: '語言設定已儲存'
  },
  model: {
    modelName: '模型名稱',
    defaultTag: '預設',
    addModelInSettings: '前往全局設定新增模型',
    loadFailed: '載入模型清單失敗',
    selectModelPlaceholder: '請選擇模型',
    builtinTag: '內建',
    editor: {
      legacyLocalUnavailable: '旧 Ollama 服务管理已停用。原记录保留；如需使用本机模型，请切换为 API 并填写 OpenAI 兼容服务地址。',
      maxOutputTokensLabel: '最大輸出 tokens',
      maxOutputTokensPlaceholder: '留空使用目錄預設',
      maxOutputTokensDesc: '單次回覆的輸出上限。留空則沿用目錄中該模型的預設值。',
      addTitle: '新增模型',
      editTitle: '編輯模型',
      sectionType: '模型類型',
      typeLabel: '模型類型',
      sectionSource: '模型來源',
      sectionProvider: '接入設定',
      sectionAdvanced: '進階選項',
      sourceLabel: '模型來源',
      sourceRemote: 'API',
      baseUrlLabel: 'Base URL',
      displayNameLabel: '顯示名稱（可選）',
      displayNamePlaceholder: '例如：客服問答模型',
      displayNameDesc: '僅用於界面展示，實際呼叫仍使用上面的模型名稱。',
      baseUrlPlaceholder: '例如：https://api.openai.com/v1',
      baseUrlPlaceholderVllm: '例如：http://localhost:11434/v1',
      baseUrlPlaceholderAsr: '例如：https://api.openai.com/v1',
      apiKeyOptional: 'API Key（可選）',
      apiKeyPlaceholder: '輸入 API Key',
      customHeadersLabel: '自定義請求頭（可選）',
      customHeadersDesc: '呼叫遠程模型 API 時附加的 HTTP 請求頭，常用於企業閘道鑑權、鏈路追蹤等情境；Authorization、Content-Type 等保留頭會被自動忽略。',
      customHeadersAdd: '新增請求頭',
      customHeadersKeyPlaceholder: 'Header 名稱',
      customHeadersValuePlaceholder: 'Header 值',
      testing: '測試中...',
      testConnection: '測試連結',
      dimensionLabel: '向量維度',
      dimensionPlaceholder: '例如：1536',
      dimensionOverrideLabel: '自定義輸出維度',
      dimensionOverrideDesc: '僅在確認該模型支持 dimensions 參數時開啟；預設只使用檢測到的實際維度。',
      supportsVisionLabel: '支持視覺/多模態',
      supportsVisionDesc: '模型是否支持圖片等多模態輸入',
      embeddingImageInputLabel: '圖片輸入',
      embeddingImageInputDesc: '模型能把圖片編碼到與文字相同的向量空間。目錄內的模型會自動識別，自訂模型需手動宣告',
      contextWindowLabel: '脈絡視窗',
      contextWindowPlaceholder: '填寫廠商公布的總上下文視窗',
      contextWindowDesc: '該模型一次請求的總上下文視窗。進階 spec 優先於此處填寫值；留空且未設定 spec 時顯示未知。請按廠商文件填寫真實值，智慧代理會預留輸出預算與壓縮餘量。',
      contextWindowUnknown: '未知',
      contextWindowTokens: '{count} tokens',
      maxConcurrencyLabel: '後台併發上限',
      maxConcurrencyPlaceholder: '0 表示使用全局預設',
      maxConcurrencyDesc: '限制文件入庫/富化等後台任務對該模型的併發呼叫數（按模型全副本共享）。0 或留空表示沿用全局預設；不影響交互式對話。',
      fillModelAndUrl: '請先填寫模型標識和 Base URL',
      remoteBaseUrlRequired: 'Remote API 類型必須填寫 Base URL',
      unsupportedModelType: '不支持的模型類型',
      saveAndClose: '儲存並關閉',
      testDraftHint: '使用當前填寫的連結設定，無需提前儲存。',
      testDraftEditHint: '使用當前填寫的連結設定；API Key 使用已單獨儲存的值。',
      testStale: '設定已修改，請重新測試。',
      connectionSuccess: '連結成功',
      connectionFailed: '連結失敗',
      connectionConfigError: '連結失敗，請檢查設定',
      providerLabel: '服務商',
      providerPlaceholder: '選擇模型服務商',
      providerDocs: '查看 {provider} 的模型文件',
      validation: {
        extraFieldRequired: '請填寫 {name}',
        modelNameRequired: '請輸入模型名稱',
        modelNameEmpty: '模型名稱不能為空',
        modelNameMax: '模型名稱不能超過100個字符',
        baseUrlRequired: '請輸入 Base URL',
        baseUrlEmpty: 'Base URL 不能為空',
        baseUrlInvalid: 'Base URL 格式不正確，請輸入有效的 URL'
      },
      modelNamePlaceholder: {
        remote: '例如：gpt-4, claude-3-opus',
        remoteVllm: '例如：gpt-4-vision-preview',
        remoteAsr: '例如：whisper-1'
      },
      description: {
        chat: '設定用於對話的大型語言模型',
        embedding: '設定用於文字向量化的內嵌模型',
        rerank: '設定用於結果重排序的模型',
        vllm: '設定用於視覺理解和多模態的視覺語言模型',
        asr: '設定用於語音辨識和音訊轉錄的語音轉文字模型',
        default: '設定模型資訊'
      },
      advanced: {
        toggle: '進階',
        compat: {
          label: '協議相容覆蓋（JSON）',
          placeholder: '{\'{\'} "max_tokens_field": "max_tokens" {\'}\'}',
          desc: '只在介面與目錄預設值不一致時填寫，只寫需要改的欄位。留空表示不覆蓋。',
          docLink: '查看欄位說明',
          invalid: 'JSON 格式不正確',
          mustBeObject: '必須是 JSON 物件'
        },
        legacyThinking: {
          label: '思考參數格式（舊設定）',
          catalog: '遵循目錄預設（推薦）',
          none: '不寫入思考參數',
          desc: '此模型仍帶有舊版 thinking_control 設定。選擇「遵循目錄預設」後由目錄決定思考參數的寫法。'
        },
        remoteModelName: {
          label: '遠端模型名',
          placeholder: '留空與模型名相同',
          desc: '實際傳送給廠商的模型 ID，與上面的模型名不同時填寫。'
        },
        api: {
          label: '協議覆蓋',
          auto: '自動（按廠商 / URL 推斷）',
          desc: '強制使用指定的請求協議；一般無需修改。'
        }
      },
      resolved: {
        title: '實際呼叫方式',
        empty: '填寫廠商與模型名後，這裡會顯示這個模型將被怎樣呼叫',
        failed: '解析失敗',
        protocol: '請求協議',
        catalog: '能力來源',
        catalogedYes: '內建模型檔案',
        catalogedNo: '廠商通用預設（未收錄此模型）',
        endpoint: '請求地址',
        thinkingFormat: '思考開關傳參',
        thinkingLevels: '可選思考強度',
        noThinking: '該模型不支持思考'
      },
      catalog: {
        reasoning: '推論',
        vision: '視覺',
        hint: '可從廠商內建目錄選擇，也可直接輸入自定義模型名。'
      }
    }
  },
  error: {
    networkError: '網路錯誤，請檢查您的網路連結',
    invalidCredentials: '使用者名或密碼錯誤',
    tokenRefreshFailed: 'Token重新整理失敗',
    pleaseRelogin: '請重新登入',
    fileSizeExceeded: '檔案大小不能超過 {size}M！',
    unsupportedFileType: '不支持的檔案類型！',
    invalidImageLink: '無效的圖片連結',
    tokenNotFound: '未找到登入權杖，請重新登入',
    streamFailed: '流式連結失敗',
    initialization: {
      checkFailed: '檢查失敗',
      testFailed: '測試失敗'
    },
    tenant: {
      listFailed: '獲取空間清單失敗',
      searchFailed: '搜尋空間失敗',
      getApiPrincipalConfigFailed: '獲取 API 使用者身份設定失敗',
      updateApiPrincipalConfigFailed: '更新 API 使用者身份設定失敗',
      createApiPrincipalTestTokenFailed: '生成 API 測試 Token 失敗',
      updateFailed: '更新空間資訊失敗',
      deleteFailed: '刪除空間失敗'
    },
    model: {
      createFailed: '建立模型失敗',
      getFailed: '獲取模型失敗',
      updateFailed: '更新模型失敗',
      deleteFailed: '刪除模型失敗'
    },
    auth: {
      loginFailed: '登入失敗',
      registerFailed: '註冊失敗',
      getUserFailed: '獲取使用者資訊失敗',
      getTenantFailed: '獲取空間資訊失敗',
      updatePreferencesFailed: '更新個性化設定失敗',
      refreshTokenFailed: '重新整理Token失敗',
      logoutFailed: '登出失敗',
      validateTokenFailed: 'Token驗證失敗'
    }
  },
  mcp: {
    testResult: {
      title: '測試結果: {name}'
    }
  },
  system: {
    globalSettings: {
      title: '系統設定',
      audit: {
        action: {
          'system.setting_changed': '系統設定變更',
          'system.admin_promoted': '授予系統管理員',
          'system.api_key_created': '建立平台 API Key',
          'system.api_key_revoked': '吊銷平台 API Key',
          'system.admin_revoked': '回收系統管理員',
          'system.user_password_reset': '重設使用者密碼',
          'system.user_created': '建立使用者',
          'system.queue_task_retried': '重新執行失敗任務',
          'system.queue_task_deleted': '清除失敗任務記錄',
          'system.queue_task_run_now': '立即執行佇列任務',
          'system.queue_task_cancelled': '終止佇列任務',
          'system.queue_archived_purged': '清除全部失敗任務'
        },
        actorRole: {
          system_admin: '系統管理員'
        }
      },
      listConfirm: {
        ssrf: {
          whitelist: {
            remove: {
              header: '移除 SSRF 白名單條目',
              body: '確認從 SSRF 白名單中移除 {entry}？移除後該條目將重新受 SSRF 防護攔截。',
              confirmBtn: '移除'
            },
            add: {
              header: '新增 SSRF 白名單條目',
              body: '確認把 {entry} 加入 SSRF 白名單？該條目比對到的主機 / IP / 網段會繞過 SSRF 防護，可能讓 Agent 存取內網服務，請僅在確知用途時新增。',
              confirmBtn: '新增'
            }
          }
        }
      },
      enumLabels: {
        auth: {
          default_tenant_mode: {
            create_personal: '自動建立個人空間',
            tenantless: '不自動建立空間'
          },
          registration_mode: {
            self_serve: '自助註冊（任何人可註冊）',
            invite_register: '僅限邀請註冊（需有效邀請連結）',
            invite_only: '禁止註冊（已有帳號仍可接受邀請）'
          }
        }
      },
      keyDescriptions: {
        model: {
          max_concurrency: '後台任務（文件入庫/富化）對單個模型的預設併發上限，按模型 ID 全副本共享。每次呼叫實時讀取，修改後立即生效、無需重啟。0 或負數表示關閉預設限制（各模型仍會尊重自身在模型管理裡設定的上限）。僅影響後台任務，不影響交互式對話。'
        },
        asynq: {
          core_concurrency: '文件解析與手工重解析的每實例保底併發，可額外借用共享彈性池；修改後需重啟。',
          postprocess_concurrency: '解析完成後的輕量收尾和富化扇出專用併發；修改後需重啟。',
          enrichment_concurrency: '摘要、圖片、圖譜與問題生成的每實例保底併發，可額外借用共享彈性池；修改後需重啟。',
          maintenance_concurrency: '資料源同步、批處理和清理任務的每實例併發，與使用者面流水線硬隔離；修改後需重啟。',
          shared_concurrency: '核心解析與內容富化共同使用的每實例彈性併發，由有積壓的一側自動借用；修改後需重啟。',
          wiki_concurrency: '每個服務實例的 Wiki 專用 Worker 併發數，與上遊任務池相互隔離。最小值為 1；修改後需重啟服務行程方可生效。'
        },
        tenant: {
          max_owned_per_user: '每個非超管使用者透過自助建立可擁有的最大空間數。每次建立空間時實時讀取，修改後立即生效。0 表示使用內建預設值 10；負數表示完全關閉限制（不建議在公開部署使用）。',
          self_service_creation_enabled: '是否允許非超管使用者主動建立空間。關閉後，普通使用者只能透過邀請加入已有空間；跨空間超管仍可建立。修改後立即生效。',
          default_storage_quota_gb: '新建空間時預設分配的存儲配額（GB），包含向量、原文、文字、索引等。僅在建立時讀取，修改後只對之後新建的空間生效，不會回寫已存在的空間。0 或負數表示使用內建預設值 10GB。',
          default_storage_quota_mb: '包括註冊自動建立的個人空間。正數優先於 GB 設定；0 或負數沿用 GB 設定。每個設定按資料庫、環境變數、內建預設值的順序讀取，僅影響之後新建的空間。',
          auto_create_api_key: '為新空間自動生成 full_access API Key，並在建立回應中返回明文 token。僅用於相容依賴舊行為的集成；預設關閉，建議透過 API Key 管理顯式建立。',
          auto_accept_invitation: '開啟後，空間管理員透過電子信箱邀請已註冊使用者時，對方會立即成為成員，不再經過收件匣確認。關閉時保持「發出邀請 → 被邀請人確認」流程。修改後立即生效。'
        },
        sandbox: {
          docker_enabled: '是否允許 Docker 沙箱後端。本機 docker.sock 等同宿主機 root，預設關閉。僅系統管理員可打開；打開後立即生效，無需重啟。私有化單機且已掛載 daemon socket，或設定了帶 TLS 的遠程 tcp:// 時再啟用。'
        },
        ssrf: {
          whitelist: 'SSRF 防護白名單。可填入 example.com / *.foo.com / 10.0.0.0/8 / 2001:db8::1。修改後立即生效。SSRF_WHITELIST_EXTRA 環境變數仍由部署方維護，不在此處覆蓋。'
        },
        auth: {
          registration_mode: '註冊模式。開放註冊允許任何人建立帳號；僅限邀請註冊要求有效邀請連結；禁止註冊不允許建立帳號，但已有帳號仍可接受邀請。儲存後立即生效。',
          default_tenant_mode: '公開註冊後的空間初始化策略。create_personal 會自動建立個人空間並授予 Owner；tenantless 僅建立帳戶，使用者需要接受邀請或主動建立空間。只影響之後註冊的使用者。',
          complex_password_enabled: '是否啟用複雜密碼。開啟後密碼必須包含大小寫字母、數字和特殊字符。修改後立即生效，只影響新註冊使用者或新密碼修改/重設操作。特殊字符包含：{specialChars}'
        }
      },
      keyLabels: {
        model: {
          max_concurrency: '模型預設併發上限'
        },
        asynq: {
          core_concurrency: '核心解析保底併發數',
          postprocess_concurrency: '後處理編排併發數',
          enrichment_concurrency: '內容富化保底併發數',
          maintenance_concurrency: '維護與同步併發數',
          shared_concurrency: '共享彈性併發數',
          wiki_concurrency: 'Wiki Worker 併發數'
        },
        tenant: {
          max_owned_per_user: '每使用者最大空間數',
          self_service_creation_enabled: '允許使用者自助建立空間',
          default_storage_quota_gb: '新空間預設存儲配額 (GB)',
          default_storage_quota_mb: '新空間預設存儲配額 (MB)',
          auto_create_api_key: '建立空間時自動生成 API Key',
          auto_accept_invitation: '邀請已註冊使用者時自動加入'
        },
        sandbox: {
          docker_enabled: '啟用 Docker 沙箱'
        },
        ssrf: {
          whitelist: 'SSRF 防護白名單'
        },
        auth: {
          registration_mode: '註冊模式',
          default_tenant_mode: '註冊預設空間策略',
          complex_password_enabled: '啟用複雜密碼'
        }
      },
      runtime: {
        queueDescriptions: {
          default: '文件解析、手工重解析',
          chat_attachment: '會話內上傳附件解析',
          postprocess: '解析收尾、富化扇出',
          summary: '文件摘要、表格摘要',
          sync: '手動與定時同步',
          low: 'FAQ 匯入、批次重解析、刪除清理',
          multimodal: '圖片 OCR、視覺描述',
          graph: '切塊圖譜抽取',
          question: '切塊問題生成',
          wiki: '內容生成、索引收尾'
        },
        queueNames: {
          default: '文件解析',
          chat_attachment: '對話附件解析',
          postprocess: '後處理編排',
          summary: '摘要生成',
          sync: '資料源同步',
          low: '維護與批處理',
          multimodal: '多模態處理',
          graph: '圖譜抽取',
          question: '問題生成',
          wiki: 'Wiki 處理'
        },
        poolDescriptions: {
          core: '文件解析與手工重解析的保底容量',
          postprocess: '解析完成後的收尾與富化扇出',
          enrichment: '摘要、圖片、圖譜與問題生成',
          maintenance: '資料源同步、批處理與刪除清理',
          shared: '由核心解析與內容富化按積壓借用',
          wiki: 'Wiki 內容生成與全局收尾'
        },
        pools: {
          core: '核心解析',
          postprocess: '後處理編排',
          enrichment: '內容富化',
          maintenance: '維護與同步',
          shared: '共享彈性',
          wiki: 'Wiki 池'
        },
        tasks: {
          taskTypes: {
            documentProcess: '文件解析',
            manualProcess: '手工重新處理',
            temporaryDocumentProcess: '聊天附件解析',
            postProcess: '文件後處理',
            summary: '摘要生成',
            tableSummary: '表格摘要生成',
            question: '問題生成',
            multimodal: '圖片多模態處理',
            graph: '知識圖譜抽取',
            sync: '資料源同步',
            faqImport: 'FAQ 匯入',
            batchReparse: '批次重新解析',
            batchDelete: '批次刪除',
            move: '文件移動',
            indexDelete: '索引刪除',
            kbClone: '知識庫複製',
            kbDelete: '知識庫刪除',
            wikiIngest: 'Wiki 內容生成',
            wikiFinalize: 'Wiki 收尾處理'
          }
        }
      }
    }
  },
  tenant: {
    title: '空間資訊',
    currentTenant: '當前空間',
    switchTenant: '切換空間',
    statusActive: '活躍',
    statusInactive: '未活化',
    statusSuspended: '已暫停',
    statusUnknown: '未知',
    loadingInfo: '正在載入資訊...',
    retry: '重試',
    unknown: '未知',
    formatError: '格式錯誤',
    searchPlaceholder: '搜尋空間名稱或輸入空間 ID...',
    noMatch: '未找到比對的空間',
    switchSuccessTitle: '已切換空間',
    switchSuccessContent: '你已進入 {name}',
    loadTenantsFailed: '載入空間清單失敗',
    loading: '載入中...',
    api: {
      title: 'API 資訊',
      userIdLabel: '使用者 ID',
      userIdDescription: '您的唯一使用者標識',
      usernameLabel: '使用者名',
      usernameDescription: '您的登入使用者名',
      createdAtLabel: '註冊時間',
      createdAtDescription: '帳戶建立的時間'
    },
    messages: {
      fetchFailed: '獲取空間資訊失敗',
      networkError: '網路錯誤，請稍後重試'
    },
    deleteDangerZone: {
      title: '刪除當前空間',
      desc: '刪除後，你將無法存取這個空間的個人檔案、對話和智慧體設定。帳號與共用知識庫會保留。',
      button: '刪除空間',
      confirmTitle: '刪除當前空間？',
      confirmBody: '確定刪除空間「{name}」？此操作無法復原。帳號與共用知識庫會保留。',
      confirmHint: '請輸入空間名稱「{name}」以確認刪除。',
      confirm: '刪除',
      nameMismatch: '空間名稱不比對',
      success: '空間已刪除',
      failed: '刪除空間失敗'
    },
    leaveDangerZone: {
      title: '退出當前空間',
      desc: '終止您在本空間的成員身份。退出後將無法存取本空間的知識庫與智慧代理，之後可被再次邀請加入。',
      button: '退出空間'
    },
    storage: {
      usageLabel: '存儲使用率'
    },
    details: {
      idLabel: '空間 ID',
      nameLabel: '空間名稱',
      descriptionLabel: '空間描述',
      businessLabel: '空間業務',
      statusLabel: '空間狀態',
      createdAtLabel: '空間建立時間',
      editName: '修改名稱',
      editNamePlaceholder: '請輸入新的空間名稱',
      editNameConfirm: '儲存',
      editNameCancel: '取消',
      editNameRequired: '空間名稱不能為空',
      editNameSuccess: '空間名稱已更新',
      editNameFailed: '更新空間名稱失敗',
      editDescription: '修改描述',
      editDescriptionPlaceholder: '請輸入新的空間描述',
      editDescriptionSuccess: '空間描述已更新',
      editDescriptionFailed: '更新空間描述失敗',
      descriptionEmptyPlaceholder: '未填寫'
    },
    create: {
      action: '建立新空間',
      dialogTitle: '建立新空間',
      dialogSubtitle: '個人檔案儲存在此空間，預設配額為 10 GB。所有帳號共用 ContextDB 知識庫。',
      nameLabel: '空間名稱',
      namePlaceholder: '例如：我的新專案',
      nameRequired: '請輸入空間名稱',
      descriptionLabel: '描述（可選）',
      descriptionPlaceholder: '簡單描述一下這個空間的用途',
      submit: '建立',
      cancel: '取消',
      success: '已建立空間',
      failed: '空間建立失敗',
      disabled: '當前系統只允許透過邀請加入空間，不能自行建立空間。'
    },
    switcher: {
      menuLabel: '切換空間',
      currentBadge: '當前',
      homeTooltip: '我的空間',
      empty: '你目前只屬於這一個空間'
    }
  },
  chat: {
    suggestedQuestions: '你可以這樣問我',
    refreshSuggestedQuestions: '換一批',
    replaceDraftTitle: '取代草稿？',
    replaceDraftBody: '使用這條推薦問題取代輸入框裡的文字。',
    historyLoadFailed: '無法載入對話記錄。',
    scrollToLatest: '跳到最新訊息',
    thinking: '思考中...',
    thinkingAlt: '正在思考',
    preparingAnswer: '正在準備回答…',
    connectingModelAndGeneratingAnswer: '正在連結模型並生成回答…',
    modelStillResponding: '模型回應較慢，仍在等待…',
    deepThoughtCompleted: '已深度思考',
    deepThoughtAlt: '深度思考完成',
    referencesTitle: '參考了{count}個相關內容',
    referencesDocCount: '引用了{count}篇文件',
    referencesWebCount: '參考了{count}條網頁',
    referencesDocAndWebCount: '引用了{docCount}篇文件和{webCount}條網頁',
    referencesDrawerTitle: '參考來源',
    referencesDrawerTitleWeb: '網頁來源',
    referencesDrawerTitleDocs: '文件來源',
    referencesDrawerTitleTools: '工具結果',
    referencesDrawerTitleMixed: '參考來源',
    referencesDrawerWebSection: '網頁',
    referencesDrawerDocsSection: '知識庫文件',
    referencesDrawerToolsSection: '工具',
    referencesDrawerEmpty: '暫無參考來源',
    questionMinimapTitle: '問答',
    questionMinimapPosition: '第 {current} 輪 · 共 {total} 輪',
    questionMinimapAriaLabel: '提問目錄',
    questionMinimapAttachmentPlaceholder: '（附件）',
    referenceChunkCount: '{count}個片段',
    fallbackHint: '未從知識庫中檢索到相關內容，以上為模型直接回答',
    truncatedHint: '回答在模型單次輸出上限處被截斷，以上為截斷前已生成的內容',
    requestInfoTitle: '請求資訊',
    requestInfoRequestId: 'Request ID',
    requestInfoMessageId: '訊息 ID',
    requestInfoSessionId: '會話 ID',
    requestInfoUrl: '請求',
    requestInfoSentAt: '發起時間',
    requestInfoEmpty: '暫無請求資訊',
    channelWeb: '網頁',
    channelApi: 'API',
    channelIm: 'IM',
    chunkLabel: '片段{index}:',
    navigateToDocument: '查看文件詳情',
    referenceSourceBack: '全部引用',
    referenceSourceView: '查看原文',
    referenceSourceRelocate: '重新定位',
    referenceSourceLocating: '正在定位引用位置…',
    referenceSourceExact: '已精確定位原文片段',
    referenceSourcePartial: '已標示核驗透過的原文片段，部分引用內容尚未比對',
    referenceSourceBlock: '已定位到來源區域，尚未精確比對文字',
    referenceSourceAmbiguous: '原文有多處相同內容，無法唯一定位',
    referenceSourceStale: '原文或內容已更新，當前引用無法精確定位',
    referenceSourcePrevious: '上一處引用',
    referenceSourceNext: '下一處引用',
    referenceSourceFoundPage: '已定位到第 {page} 頁',
    referenceSourceNotFound: '未能精確定位引用內容，已為你打開原文',
    referenceSourceOpenWeb: '打開原網頁並定位',
    chunkIdLabel: '片段ID:',
    documentIdLabel: '文件ID:',
    faqIdLabel: 'FAQ ID:',
    faqContainerIdLabel: '所屬文件ID:',
    faqAnswersLabel: '答案:',
    chunkOrdinal: '片段 {index}',
    previewContent: '預覽內容',
    noPlanSteps: '未提供具體步驟',
    chunkIndexLabel: '片段 #{index}',
    chunkPositionLabel: '(位置: {position})',
    noRelatedChunks: '沒有找到相關片段',
    noSearchResults: '沒有找到搜尋結果',
    relevanceHigh: '高相關',
    relevanceMedium: '中相關',
    relevanceLow: '低相關',
    relevanceWeak: '弱相關',
    webSearchNoResults: '未找到搜尋結果',
    otherSource: '其他來源',
    webGroupIntro: '以下 {count} 條內容來自',
    graphConfigTitle: '圖譜設定',
    entityTypesLabel: '實體類型:',
    relationTypesLabel: '關係類型:',
    graphResultsHeader: '找到 {count} 條相關結果',
    graphNoResults: '未找到相關的圖譜資訊',
    unknownLink: '未知連結',
    contentLengthLabel: '長度 {value}',
    notProvided: '未提供',
    errorMessageLabel: '錯誤資訊',
    summaryLabel: '總結',
    rawTextLabel: '原始文字',
    collapseRaw: '收起原文',
    expandRaw: '展開原文',
    noWebContent: '未獲取到網頁內容',
    webFetchStatusSuccess: '抓取成功',
    webFetchStatusFailed: '抓取失敗',
    webFetchStatusSkipped: '已跳過',
    webFetchErrorCode: '錯誤碼',
    webFetchRetryable: '可重試',
    webFetchContentRange: '字符範圍 {start}–{end}，共 {total} 字符',
    webFetchPartialContent: '部分頁面內容',
    webFetchSummaryFailed: '摘要失敗',
    lengthChars: '{value} 字',
    lengthThousands: '{value} 千字',
    lengthTenThousands: '{value} 萬字',
    noDatabaseRecords: '未找到比對的記錄',
    nullValuePlaceholder: '<NULL>',
    chunkCountValue: '{count} 個片段',
    documentDescriptionLabel: '文件描述:',
    documentSourceLabel: '來源:',
    documentFileLabel: '檔案資訊:',
    documentMetadataLabel: '元資料',
    documentInfoEmpty: '暫無文件資訊',
    positionLabel: '位置:',
    chunkPositionValue: '第 {index} 個片段',
    contentLengthLabelSimple: '內容長度:',
    fullContentLabel: '完整內容',
    copyContent: '複製內容',
    knowledgeBaseCount: '共 {count} 個知識庫',
    noKnowledgeBases: '沒有可用的知識庫',
    rawOutputLabel: '原始輸出',
    wikiWritePageTitle: 'Wiki 頁面寫入',
    wikiReplaceTextTitle: 'Wiki 文字取代',
    wikiRenamePageTitle: 'Wiki 頁面重新命名',
    wikiDeletePageTitle: 'Wiki 頁面刪除',
    wikiActionCreated: '已建立',
    wikiActionUpdated: '已更新',
    wikiActionRenamed: '已重新命名',
    wikiActionDeleted: '已刪除',
    wikiFieldSlug: '頁面路徑',
    wikiFieldTitle: '標題',
    wikiFieldPageType: '類型',
    wikiFieldSummary: '摘要',
    wikiFieldOldText: '原文字',
    wikiFieldNewText: '新文字',
    wikiFieldOldSlug: '原路徑',
    wikiFieldNewSlug: '新路徑',
    wikiFieldAffectedPages: '受影響頁面',
    wikiAffectedCount: '{count} 個頁面的連結已更新',
    processError: '處理出錯',
    sessionExcerpt: '會話摘錄',
    noAnswerContent: '（無回答內容）',
    manualSourcesHeading: '參考來源',
    noMatchFound: '未找到比對的內容',
    deleteSessionFailed: '刪除失敗，請稍後再試！',
    imageTooMany: '最多上傳5張圖片',
    imageTypeSizeError: '僅支持 JPG/PNG/GIF/WEBP 格式，單張不超過 10MB',
    imageUploadTooltip: '上傳圖片（支持貼上/拖曳）',
    attachmentUploadTooltip: '上傳附件（文件、音訊等）',
    attachmentWithCount: '已上傳 {count} 個附件',
    attachmentTooMany: '最多上傳 {max} 個附件',
    attachmentTotalTooMany: '圖片和附件合計最多 {max} 個',
    attachmentTooLarge: '檔案 {name} 超過 {max}MB 限制',
    attachmentTypeNotSupported: '不支持的檔案類型：{name}',
    attachmentUploading: '上傳中 {progress}%',
    attachmentParsing: '正在解析',
    attachmentReady: '解析完成',
    attachmentUploadFailed: '附件上傳失敗',
    attachmentParseFailed: '附件解析失敗',
    attachmentStillProcessing: '附件 {name} 仍在解析，請稍候',
    memoryUsedCount: '本次使用了 {count} 條記憶',
    memoryForget: '刪除這條記憶',
    memoryForgotten: '已刪除這條記憶',
    memoryForgetFailed: '刪除失敗',
    memoryHint: '這些是助手在回答時看到的長期記憶，刪除後不會再被使用。',
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
      loading: '正在載入輸出…',
      unavailable: '暫時無法查看輸出',
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
      tooltip: '回滾到這裡',
      confirmTitle: '回滾到這裡？',
      confirmBody: '此條之後的對話將被刪除；從提問回滾時，該問題會填回輸入框。有檢查點時工作區也會一併回退，操作不可復原。',
      confirmButton: '回滾',
      cancelButton: '取消',
      success: '已回滾',
      reloadFailed: '對話已回滾，但未能重新載入歷史。若較早訊息缺失，請重新整理頁面',
      failed: '回滾失敗，請重試',
      skipped: '對話已回滾，工作區未改動',
      skipNoSandbox: '對話已回滾，工作區未改動（當前沒有沙箱）',
      skipNoCheckpoint: '對話已回滾，工作區未改動（沒有可回退的檢查點）'
    },
    sandbox: {
      panelTitle: '沙箱可視化',
      tabArtifacts: '產物',
      tabTerminal: '終端',
      tabDesktop: '桌面',
      artifactsEmpty: '本會話尚未生成可下載的檔案',
      artifactScope: '產物範圍',
      artifactsCurrent: '本輪',
      artifactsAll: '全部',
      artifactsSearch: '搜尋檔名',
      artifactsNoMatches: '沒有比對的檔案',
      desktopNotStarted: '桌面尚未連結。連結後會接入本會話的沙箱環境。',
      desktopStart: '連結桌面',
      desktopStarting: '正在連結桌面…（首次約需 3–8 秒）',
      desktopUnsupported: '當前沙箱設定不支持桌面。需要在工作區沙箱設定的模板清單裡選中帶桌面的映像，且後端為 Cube 或 E2B。',
      desktopBusy: '本會話已有一個桌面連結。桌面同一時刻只允許一個連結，否則會出現兩個人搶同一套鍵鼠。',
      desktopStartFailed: '桌面啟動失敗，可以重試。',
      desktopRebuilt: '沙箱已因技能更新重建，原桌面及未儲存的內容已丟失。重新連結會得到一個全新桌面。',
      desktopNeedsProvision: '本會話當前沒有運行中的沙箱環境。建立並連結會新建一個沙箱，並按工作區設定計費。',
      desktopCreateAndStart: '建立並連結',
      desktopPaused: '本會話的沙箱已暫停。連結桌面會喚醒它。',
      desktopDisconnected: '桌面連結已斷開',
      desktopIdleDisconnected: '桌面空閒已斷開，沙箱將按工作區 TTL 自行暫停。可重新連結。',
      desktopRetry: '重新連結',
      paused: '本會話的沙箱已暫停。啟動終端會喚醒它。',
      stopped: '本會話的沙箱未在執行：可能已停止，或因長時間閒置已被回收。啟動終端會重新啟動它；若已被回收，則會新建一個沙箱，先前的檔案和安裝的軟體不會保留。',
      start: '啟動終端',
      connecting: '正在連結沙箱…',
      needsProvision: '本會話當前沒有運行中的沙箱環境。建立並啟動會新建一個沙箱，並按工作區設定計費。',
      createAndStart: '建立並啟動',
      noSandbox: '會話尚未建立沙箱，且當前智慧代理未設定沙箱後端，無法確定在哪個後端建立。請切換到設定了沙箱的智慧代理，或傳送一條需要執行程式碼的訊息。',
      unsupported: '當前沙箱後端不支持交互終端',
      disconnected: '連結已斷開',
      retry: '重新連結',
      sessionEnded: '終端會話已結束',
      idleDisconnected: '終端空閒已斷開，沙箱將按工作區 TTL 自行暫停。可重新連結。',
      idleDisconnectedNewShell: '終端閒置已斷開，其中的 shell 已結束（nohup 啟動的背景任務不受影響）。重新連結會開啟一個新的 shell。',
      disconnectedNewShell: '連結已斷開，終端中的 shell 已結束（nohup 啟動的背景任務不受影響）。重新連結會開啟一個新的 shell。',
      authRevoked: '登入狀態已失效，終端已斷開。請重新登入後再連結。'
    },
    conversationTime: {
      today: '今天 {time}',
      yesterday: '昨天 {time}',
      thisYear: '{month}月{day}日 {time}',
      otherYear: '{year}年{month}月{day}日 {time}'
    }
  },
  knowledgeEditor: {
    titleCreate: '新建知識庫',
    titleEdit: '知識庫設定',
    advanced: {
      title: '進階設定',
      description: '設定問題生成等進階功能',
      multimodal: {
        label: '多模態功能',
        description: '啟用圖片等多模態內容的理解能力',
        vllmLabel: 'VLLM 視覺模型',
        vllmDescription: '用於多模態理解的視覺語言模型（必選）',
        vllmPlaceholder: '請選擇 VLLM 模型（必選）',
        descriptionLanguageLabel: '圖片描述語言',
        descriptionLanguageDescription: '留空時跟隨文件語言；不再強制使用中文',
        descriptionLanguageAuto: '自動跟隨文件語言',
        customInstructionsLabel: '圖片解析要求',
        customInstructionsDescription: '補充需要重點識別的視覺資訊，OCR 和 Markdown 格式協議保持不變',
        customInstructionsPlaceholder: '例如：重點識別裝置銘牌、型號、告警程式碼和表格中的單位…',
        imageVectorLabel: '圖片向量檢索',
        imageVectorDescription: '開啟後，產生圖片描述之後再用向量模型直接對圖片編碼，檢索時可依圖片內容找回描述中沒寫到的資訊。需要向量模型支援圖片輸入；每張圖片多一次向量呼叫，向量檢索的候選範圍也會擴大。僅對之後匯入或重新解析的文件生效，掃描版 PDF 頁面不會產生',
        imageVectorModelUnsupported: '目前的向量模型未宣告支援圖片輸入，開啟後不會產生或檢索圖片向量',
        imageAttrsSchemaLabel: '可觀察的圖片屬性',
        imageAttrsSchemaDescription: '模型會觀察以下屬性（由後端登錄檔定義）以驅動 OCR 策略',
        imagePipelineSectionLabel: '圖片解析方案',
        imagePipelineSectionDescription: '多模態解析開啟後，可以根據需要選擇圖片的解析方案',
        imagePipelineLabel: '選擇解析方案',
        advancedSettingsLabel: '進階設定',
        notesLabel: '附加說明',
        imagePipelinePlaceholder: '請選擇解析方案',
        imagePipelineLoading: '正在讀取流水線…',
        imagePipelineLoadError: '讀取流水線失敗',
        imagePipelineValidateError: '無法校驗當前設定，儲存時後端會再次檢查。',
        imageAttrsOcrConditions: '根據觀察到的屬性條件觸發 OCR',
        imageAttrsOcrConditionsDesc: '當觀察到的屬性滿足以下條件時，對圖片進行 OCR',
        imagePipelineKbNote: '預設跟隨知識庫設定，可針對本次任務調整'
      },
      tableMetadataInstructions: {
        label: '表格元資料生成要求',
        description: '為 CSV/Excel 摘要補充業務背景和欄位語義，幫助後續檢索理解表格內容',
        placeholder: '例如：這是銷售訂單表，金額單位為元，status 欄位使用公司內部狀態碼…'
      },
      autoTag: {
        label: '自動關聯標籤',
        description: '文件解析完成後，從當前知識庫已有標籤中選擇合適標籤自動關聯。不會建立或刪除標籤，並會增加一次模型呼叫。',
        modelLabel: '分類模型',
        modelDescription: '留空時使用知識庫摘要模型。',
        modelPlaceholder: '請選擇分類模型',
        maxTagsLabel: '單篇文件最多標籤數',
        maxTagsDescription: '每篇文件最多自動關聯 1-10 個已有標籤。',
        skipIfTaggedLabel: '跳過已有標籤的文件',
        skipIfTaggedDescription: '開啟後，上傳時已手動設定標籤的文件不再自動打標籤，避免覆蓋人工分類意圖。'
      },
      profile: {
        label: '自動生成知識庫描述',
        description: '文件新增、刪除或摘要更新後，從文件畫像聚合自動生成知識庫描述。聚合本身不呼叫模型，僅當聚合結果變化時才發起一次小模型呼叫。',
        modelLabel: '生成模型',
        modelDescription: '留空時使用知識庫摘要模型。',
        modelPlaceholder: '請選擇生成模型',
        instructionsLabel: '描述生成要求',
        instructionsDescription: '補充面向的讀者、需要保留的術語或表達風格，系統仍維護穩定的輸出格式。',
        instructionsPlaceholder: '例如：面向售後客服，用通俗說法描述產品線，保留產品型號…'
      },
      questionGeneration: {
        modelLabel: '問題生成模型',
        modelDescription: '留空時使用知識庫的摘要模型。',
        modelPlaceholder: '選擇問題生成模型',
        label: 'AI 問題生成',
        description: '解析文件時呼叫大型語言模型為每個切塊生成相關問題，提高檢索召回率。啟用後會增加文件解析耗時。',
        countLabel: '生成問題數量',
        countDescription: '每個文件切塊生成的問題數量（1-10）',
        instructionsLabel: '問題生成要求',
        instructionsDescription: '指定問題面向的人群、情境和表達方式，系統仍維護穩定輸出格式',
        instructionsPlaceholder: '例如：生成客服使用者常問的自然語言問題，避免考試題式表達…'
      }
    },
    asr: {
      title: '音訊語音辨識',
      description: '設定語音辨識（ASR），啟用後可上傳音訊檔案並整段轉寫為文字（常見格式：mp3、wav、m4a、flac、ogg 等）。暫不支持影片上傳。',
      label: '啟用音訊語音辨識',
      desc: '啟用後可上傳音訊到知識庫，系統自動將語音轉寫為文字並參與解析與檢索',
      modelLabel: 'ASR 模型',
      modelDescription: '用於音訊中語音轉文字的識別模型（如 OpenAI Whisper）',
      modelPlaceholder: '請選擇 ASR 模型',
      languageLabel: '音訊語言提示',
      languageDescription: '可選；指定主要語種可提高部分 ASR 模型的識別穩定性，留空時自動檢測',
      languagePlaceholder: '例如 zh、en，留空自動檢測'
    },
    multimodal: {
      title: '影像處理設定',
      description: '設定影像內容理解能力，啟用後支持圖片等非文字內容的解析和檢索'
    },
    chunking: {
      title: '切塊設定',
      description: '控制上傳文件在內嵌前的切分方式。預設值適用於大多數情境，僅在檢索品質例外時調整。',
      sizeLabel: '切塊大小',
      sizeDescription: '每個切塊的最大字符數（100-4000）。預設 512 ≈ 中文 300 tokens / 英文 100-130 tokens。FAQ 用 200-400，敘述性長文件用 1000-2000。',
      characters: '字符',
      overlapLabel: '切塊重疊',
      overlapDescription: '相鄰切塊之間共享的字符數（0-500）。預設 80 ≈ 切塊大小的 15%，符合當前研究推薦。FAQ/結構化資料用 0，長篇敘述用 150-200。',
      separatorsLabel: '分隔符',
      separatorsDescription: '切分時優先使用的字符或字符串。優先級高的分隔符先嘗試；預設順序優先段落 → 句子 → 標點。',
      separatorsPlaceholder: '選擇或自定義分隔符',
      parentChildLabel: '父子切塊',
      parentChildDescription: '兩級切塊：小的子塊用於向量比對（精準命中），大的父塊返回給 LLM（更豐富脈絡）。建議用於長文件（>10 頁）；短 FAQ 可關閉以節省存儲。',
      parentChunkSizeLabel: '父塊大小',
      parentChunkSizeDescription: '返回給 LLM 的脈絡塊大小（512-8192）。預設 4096 ≈ 1000 英文 tokens，適合所有現代 LLM 脈絡視窗。',
      childChunkSizeLabel: '子塊大小',
      childChunkSizeDescription: '用於向量比對的內嵌塊大小（64-2048）。預設 384 ≈ 80 tokens，是 sentence-transformer / BGE 類內嵌模型的最佳點。',
      strategyLabel: '切塊策略',
      strategyDescription: '選擇文件的切塊方式。自動模式會分析每個文件的結構並選擇最佳策略。',
      strategyPlaceholder: '選擇切塊策略（不填則按長度切分）',
      overlapWarning: '重疊相對於切塊大小較大──切塊之間會共享大部分內容。',
      advancedLabel: '進階選項',
      tokenLimitLabel: '每塊 Token 上限',
      tokenLimitDescription: '每個切塊的硬性 Token 上限（0-8192）。0 = 關閉（僅按字符數）。當內嵌模型 Token 上限較小時啟用：MiniLM (256 tok) 用 200，BGE/Cohere (512 tok) 用 400。現代內嵌器（OpenAI、Voyage、Jina-v3）支持 >2000 tokens，保持 0 即可。',
      languagesLabel: '語言提示',
      languagesDescription: '限制啟發式模式只識別選定的語言（DE/EN/ZH）。留空 = 自動檢測。同質化語料庫可顯式設定以避免跨語言誤比對。',
      languagesPlaceholder: '自動檢測',
      debug: {
        toggle: '測試切塊效果',
        toggleHint: '無需重新上傳即可對示例文字運行切塊器',
        sampleLabel: '示例文字',
        samplePlaceholder: '貼上 Markdown / 純文字片段以查看當前設定的切塊結果…',
        presetLabel: '載入示例：',
        runButton: '運行預覽',
        loading: '正在對示例運行切塊器…',
        errorPrefix: '預覽失敗',
        selectedTier: '選定策略',
        rejected: '被拒絕的層級',
        contextHeader: '脈絡標題',
        fallbackWarning: '策略鏈已窮盡 — 當前設定無法智慧切塊此內容',
        stats: {
          chunks: '塊',
          truncated: '已截斷；總數 {total}'
        },
        profile: {
          lines: '行',
          chars: '字符',
          headings: 'Markdown 標題',
          pageBreaks: '分頁符',
          chapterMarkers: '章節標記',
          languages: '語言'
        },
        samples: {
          markdown: 'Markdown 文件',
          faq: 'FAQ 清單',
          chapter: 'PDF 章節',
          plain: '純文字'
        }
      },
      languageOptions: {
        de: '德語',
        en: '英語',
        zh: '中文'
      },
      strategies: {
        legacy: {
          label: '按長度切分',
          tooltip: '忽略結構，僅按字符數和分隔符遞迴切分──原始行為。當上述策略對你的內容效果不佳時使用。'
        },
        heuristic: {
          label: '結構感知',
          tooltip: '識別分頁符、編號章節、多語言章節標記（DE/EN/ZH）、全大寫標題等結構信號進行切分。適合沒有 Markdown 標題的 PDF / 掃描件。'
        },
        heading: {
          label: '按標題切分',
          tooltip: '在 Markdown 標題（#、##、###）邊界處切分，每塊自動帶上所在標題路徑。適合結構清晰的 Markdown 文件。'
        },
        auto: {
          label: '自動',
          tooltip: '文件分析器根據內容結構自動在「按標題切分」「結構感知」「按長度切分」之間選擇。'
        }
      },
      separators: {
        doubleNewline: '雙換行 (\\n\\n)',
        singleNewline: '單換行 (\\n)',
        periodCn: '中文句號 (。)',
        exclamationCn: '感嘆號 (！)',
        questionCn: '問號 (？)',
        semicolonCn: '中文分號 (；)',
        semicolonEn: '英文分號 (;)',
        space: '空格 ( )'
      }
    },
    models: {
      title: '模型設定',
      description: '為知識庫選擇合適的 AI 模型',
      llmLabel: 'LLM 大型語言模型',
      llmDesc: '用於總結和摘要的大型語言模型',
      llmPlaceholder: '請選擇 LLM 模型（可選）',
      embeddingLabel: 'Embedding 內嵌模型',
      embeddingDesc: '用於文字向量化的內嵌模型',
      embeddingPlaceholder: '請選擇 Embedding 模型',
      embeddingLocked: '知識庫中已有檔案，無法修改 Embedding 模型',
      embeddingOptional: '（可選）',
      embeddingWikiOptionalDesc: '可選。設定後用於 Wiki 目錄歸類的相似度比對，讓新頁面更好地復用已有目錄；不設定則按完整目錄樹歸類。'
    },
    faqImport: {
      title: '批次匯入 FAQ'
    },
    faq: {
      title: '問答',
      description: '設定 FAQ 知識庫的索引策略和問答組織方式',
      indexModeLabel: '索引方式',
      indexModeDescription: '僅索引問題可提升精度，索引問答可提高召回率',
      questionIndexModeLabel: '問題索引方式',
      questionIndexModeDescription: '合併索引：標準問和相似問合併索引；分別索引：標準問和每個相似問獨立索引，檢索更精確但需要更多存儲',
      entryGuide: 'FAQ 條目由標準問、相似問、反例和多個答案組成，可在知識庫詳情中批次匯入、編輯。',
      modes: {
        questionOnly: '僅標準問/相似問',
        questionAnswer: '標準問 + 答案',
        combined: '合併索引',
        separate: '分別索引'
      }
    },
    document: {
      title: '文件'
    },
    messages: {
      loadModelsFailed: '載入模型清單失敗',
      loadDataFailed: '載入知識庫資料失敗',
      notFound: '知識庫不存在',
      nameRequired: '請輸入知識庫名稱',
      summaryRequired: '請選擇 Summary 模型',
      multimodalInvalid: '多模態設定驗證失敗',
      createSuccess: '已建立知識庫',
      createFailed: '建立知識庫失敗',
      missingId: '缺少知識庫 ID',
      buildDataFailed: '資料建構失敗',
      updateSuccess: '設定已儲存',
      indexModeRequired: '請選擇 FAQ 的索引方式',
      storageChangeConfirm: '知識庫中已有檔案，更改存儲引擎後舊檔案可能無法正常存取。是否確認更改？'
    },
    share: {
      description: '將知識庫共享給空間，讓空間成員可以存取和使用',
      hintTitle: '共享說明',
      addShare: '共享',
      unshareConfirm: '確定要取消對「{name}」的共享嗎？',
      tip1: '共享後，空間成員將根據設定的權限存取此知識庫',
      tip2: '可編輯權限允許成員修改知識庫內容，唯讀權限僅允許檢索和問答'
    },
    postCreateHint: {
      title: '建立成功',
      footer: '可繼續調整設定，設定共享與資料源，完成後點擊「儲存並關閉」。',
      followUpDesc: '可在左側設定資料源，或在「共享管理」中發布到空間'
    },
    footer: {
      instantEffect: '此頁的更改即時生效，無需儲存'
    },
    buttons: {
      create: '建立知識庫',
      saveAndClose: '儲存並關閉'
    },
    wikiBrowser: {
      viewInGraph: '在圖譜中查看',
      filterSummary: '摘要',
      filterEntity: '實體',
      filterConcept: '概念',
      filterSynthesis: '綜合',
      filterComparison: '對比',
      version: 'v{ver}',
      gallery: {
        attr: {
          builtin_caption: '描述',
          builtin_caption_description: '模型生成的圖片描述',
          builtin_ocr_text: 'OCR 文字',
          builtin_ocr_text_description: 'OCR 從圖片中提取的文字',
          builtin_page: '文件頁碼',
          builtin_page_description: '依來源文件分組，再依 PDF 頁碼排序；未知頁碼放在文件末尾。',
          builtin_created_at: '建立時間',
          builtin_created_at_description: '所屬文件片段的建立時間',
          builtin_updated_at: '更新時間',
          builtin_updated_at_description: '所屬文件片段的最後更新時間',
          builtin_is_enabled: '啟用狀態',
          builtin_is_enabled_description: '所屬文件片段是否參與檢索',
          builtin_is_enabled_value_true: '已啟用',
          builtin_is_enabled_value_false: '已停用'
        }
      }
    },
    indexing: {
      title: '索引策略',
      description: '設定文件上傳後的處理管道，可以獨立開啟或關閉每種索引方式',
      searchTitle: 'RAG 檢索',
      searchDesc: '對文件進行切塊、向量化和關鍵字索引，支持混合檢索',
      wikiTitle: 'Wiki 知識庫',
      wikiDesc: '自動生成互相關聯的 Wiki 知識頁面，建構結構化知識體系',
      atLeastOne: '至少需要開啟一種索引策略',
      embeddingRequired: 'RAG 檢索需要設定 Embedding 模型',
      lockedTip: '知識庫已有內容，索引策略暫不支持調整。如需變更，請先清空知識庫。',
      rebuildConfirmTitle: '重建索引',
      rebuildConfirmBody: '索引策略已變更，是否對已有的 {count} 篇文件重新處理？這可能需要一些時間。',
      rebuildSuccess: '已提交重建任務，共 {count} 篇文件',
      rebuildSkip: '稍後可在資料源中手動觸發重建'
    },
    wiki: {
      title: 'Wiki 設定',
      synthesisModelLabel: 'Wiki 合成模型',
      synthesisModelPlaceholder: '選擇用於 Wiki 生成的 LLM 模型',
      synthesisModelTip: '不設定時將回退使用摘要模型',
      autoGenerateLabel: '自動生成 Wiki 頁面',
      autoGenerateTip: '關閉後仍可瀏覽和手動維護 Wiki 頁面，但文件處理不會自動呼叫 LLM 生成或更新頁面',
      extractionGranularityLabel: '提取粒度',
      contentInstructionsLabel: 'Wiki 內容生成要求',
      contentInstructionsTip: '控制摘要、頁面和首頁的表達重點；引用、合併與防幻覺規則由系統固定維護。修改後需重新解析才能影響已有內容。',
      contentInstructionsPlaceholder: '例如：使用法務審閱口吻，優先展示責任主體、時間軸和風險提示…',
      extractionInstructionsLabel: 'Wiki 提取重點',
      extractionInstructionsTip: '說明應重點識別的領域實體和概念，不會取代系統的 JSON 與引用協議。',
      extractionInstructionsPlaceholder: '例如：重點識別產品、版本、組織、負責人和關鍵技術概念…',
      extractionGranularityTip: '控制每篇文件抽取的 Wiki 實體/概念數量。粒度越細，索引越聚焦；粒度越粗，索引越詳盡',
      granularityFocused: '聚焦',
      granularityStandard: '標準',
      granularityExhaustive: '詳盡',
      granularityFocusedHint: '只抽取文件的主角（如履歷 → 人物和專案）。最乾淨，但可能漏掉次要實體。',
      granularityStandardHint: '抽取主角 + 被詳細描述的次要實體/概念。跳過一帶而過的通用名詞。適合大多數情境。',
      granularityExhaustiveHint: '抽取所有可識別的命名實體與概念，包括一帶而過的技術棧。適合將知識庫當作術語表使用。'
    },
    basic: {
      title: '基本資訊',
      description: '設定知識庫的名稱和描述資訊',
      kbId: '知識庫 ID',
      kbIdDesc: 'API 集成時可使用此 ID 指定知識庫',
      typeLabel: '知識庫類型',
      typeDocument: '文件',
      typeFAQ: '問答',
      typeDescription: 'FAQ 類型適合結構化問答資料；文件型支持檔案解析與切塊；Wiki 類型由 LLM 自動建構互鏈知識頁面。',
      nameLabel: '知識庫名稱',
      namePlaceholder: '請輸入知識庫名稱',
      descriptionLabel: '知識庫描述',
      descriptionPlaceholder: '請輸入知識庫描述（可選）',
      profile: {
        title: 'AI 生成描述',
        hint: '由文件畫像聚合生成，不會覆蓋上方手寫描述；智慧代理會同時讀取兩者來判斷問題是否該在本知識庫中檢索。',
        empty: '尚未生成。上傳文件並生成摘要後，點擊下方按鈕即可生成。',
        noDocuments: '知識庫中還沒有已解析完成的文件。',
        questions: '典型問題',
        generate: '生成 AI 描述',
        regenerate: '重新生成',
        adopt: '用作知識庫描述',
        generated: 'AI 描述已生成',
        generateFailed: 'AI 描述生成失敗',
        adopted: '已填入知識庫描述，儲存後生效',
        failed: '上次生成失敗：{error}',
        generatedAt: '生成於 {time} · 基於 {count} 篇文件'
      }
    },
    errors: {
      vectorStoreBindingInvalid: '無法使用所選向量存儲。請選擇其他存儲或使用系統預設值。',
      vectorStoreUnavailable: '所選向量存儲當前不可用。請在設定 → 向量存儲中檢查其連結設定。'
    },
    sidebar: {
      basic: '基本資訊',
      models: '模型設定',
      vectorStore: '向量存儲',
      chunking: '切塊設定',
      storage: '存儲引擎',
      advanced: '進階設定',
      faq: 'FAQ 設定',
      graph: '知識圖譜',
      multimodal: '影像處理',
      asr: '音訊處理',
      datasource: '資料源',
      share: '共享管理',
      activity: '活動記錄'
    },
    navGroups: {
      basic: '基礎',
      processing: '索引與解析',
      data: '存儲與資料',
      integration: '發布集成',
      management: '管理與稽核'
    },
    activity: {
      title: '活動記錄',
      description: '查看這個知識庫的重要變更與後台任務入口，記錄預設遵循稽核日誌保留策略。',
      allOutcomes: '全部結果',
      allActions: '全部操作',
      refresh: '重新整理',
      retry: '重試',
      empty: '暫無活動記錄',
      emptyFiltered: '沒有比對的活動記錄',
      clearFilters: '清除篩選',
      loadingMore: '載入中…',
      end: '沒有更早的記錄了',
      loadFailed: '活動記錄載入失敗',
      systemActor: '系統觸發',
      actorWithAPIKey: '{actor} · API Key · {name}',
      actorAPIKey: 'API Key · {name}',
      viaAssistant: '經小知助手',
      knowledgeBase: '知識庫',
      countItems: '共 {count} 項',
      titleWithCount: '{title} 等 {count} 項',
      importSummary: '成功 {success} / 失敗 {failed} / 跳過 {skipped}',
      detailValues: {
        user: '使用者發起',
        manual: '手動觸發',
        schedule: '定時調度',
        system: '系統觸發',
        pending: '待處理',
        completed: '已完成',
        partial: '部分完成',
        canceled: '已取消',
        failed: '失敗',
        enqueue: '任務提交',
        reuse_vectors: '復用向量',
        reparse: '重新解析',
        viewer: '唯讀',
        editor: '可編輯',
        admin: '管理',
        append: '追加',
        replace: '覆蓋'
      },
      outcomes: {
        accepted: '已受理',
        success: '成功',
        failed: '失敗',
        partial: '部分完成',
        canceled: '已取消',
        denied: '已拒絕'
      },
      actions: {
        'kb.created': '建立知識庫',
        'kb.updated': '更新知識庫',
        'kb.deleted': '刪除知識庫',
        'kb.duplicated': '複製知識庫',
        'kb.clone_started': '開始克隆',
        'kb.clone_completed': '完成克隆',
        'kb.clone_failed': '克隆失敗',
        'knowledge.created': '新增知識',
        'knowledge.updated': '更新知識',
        'knowledge.deleted': '刪除知識',
        'knowledge.batch_deleted': '批次刪除知識',
        'knowledge.reparse_started': '開始重新解析',
        'knowledge.parse_canceled': '取消解析',
        'knowledge.move_started': '開始移動知識',
        'knowledge.move_completed': '完成移動知識',
        'knowledge.move_failed': '移動知識失敗',
        'tag.created': '建立標籤',
        'tag.updated': '更新標籤',
        'tag.deleted': '刪除標籤',
        'datasource.created': '建立資料源',
        'datasource.updated': '更新資料源',
        'datasource.deleted': '刪除資料源',
        'datasource.sync_started': '開始同步資料源',
        'datasource.sync_completed': '資料源同步完成',
        'datasource.sync_failed': '資料源同步失敗',
        'datasource.paused': '暫停資料源',
        'datasource.resumed': '復原資料源',
        'kb.share_added': '新增共享',
        'kb.share_permission_changed': '修改共享權限',
        'kb.share_removed': '移除共享',
        'wiki.content_changed': '更新 Wiki 內容',
        'faq.import_started': '開始匯入 FAQ',
        'faq.import_completed': '完成匯入 FAQ',
        'faq.import_failed': '匯入 FAQ 失敗'
      },
      detailFields: {
        task_id: '任務 ID',
        trigger: '觸發方式',
        processing_status: '處理狀態',
        source_kb_id: '來源知識庫 ID',
        target_kb_id: '目標知識庫 ID',
        sync_log_id: '同步記錄 ID',
        mode: '執行模式',
        attempt: '處理批次',
        count: '專案數',
        total: '總數',
        processed: '已處理',
        failed: '失敗數',
        skipped: '跳過數',
        failure_stage: '失敗階段'
      },
      targets: {
        knowledge_base: '知識庫',
        knowledge: '知識',
        faq_entry: 'FAQ 條目',
        knowledge_tag: '標籤',
        data_source: '資料源',
        knowledge_base_share: '共享',
        knowledge_move: '知識移動',
        wiki: 'Wiki'
      },
      drawer: {
        sectionSummary: '摘要',
        sectionIdentifiers: '標識符',
        sectionTask: '任務資訊',
        targetChange: '變更詳情'
      },
      expanded: {
        targetType: '物件類型',
        targetId: '物件 ID',
        actorId: '發起人 ID',
        apiKeyName: 'API Key 名稱',
        apiKeyId: 'API Key ID',
        agentSessionId: '助手對話 ID',
        agentOperation: '助手操作',
        details: '詳情'
      },
      columns: {
        time: '時間',
        action: '操作',
        target: '物件',
        actor: '發起人',
        outcome: '結果'
      }
    }
  },
  embedPublish: {
    copyCode: '複製程式碼'
  },
  knowledgeList: {
    detail: {
      title: '共享知識庫',
      sourceOrg: '來源空間',
      myPermission: '我的權限'
    },
    sections: {
      tenantOthers: '本空間 · 其他成員',
      tenantReadonly: '本空間 · 僅查看'
    },
    empty: {
      title: '暫無知識庫'
    }
  },
  createChat: {
    title: 'Hi，我是小知，讓你的知識觸手可及',
    newSessionTitle: '新會話',
    openProject: '選擇專案',
    clearProject: '取消綁定',
    pickFailed: '無法打開所選路徑',
    messages: {
      createFailed: '建立會話失敗',
      createError: '建立會話失敗，請稍後重試'
    }
  },
  input: {
    addModel: '新增模型',
    placeholder: '輸入問題或描述任務…',
    agentMode: '智慧推論',
    normalMode: '快速問答',
    normalModeDesc: '基於知識庫的 RAG 問答',
    agentModeDesc: '多步思考，深度分析',
    agentMissingAllowedTools: '允許的工具',
    agentMissingSummaryModel: '對話模型',
    agentMissingRerankModel: '重排模型',
    customAgentMissingSummaryModel: '對話模型',
    customAgentMissingRerankModel: '重排模型',
    goToAgentEditor: '前往設定 →',
    agentNotReadyDetail: '智慧代理「{agentName}」未就緒，需要設定以下內容：{reasons}',
    sharedAgentNotReadyDetail: '共享智慧代理「{agentName}」尚未就緒（缺少：{reasons}），請聯絡分享方管理員完成設定。',
    knowledgeBase: '知識庫',
    knowledgeBaseWithCount: '知識庫({count})',
    notConfigured: '未設定',
    sharedAgentModelLabel: '共享智慧代理設定的模型',
    noModel: '暫無可用模型',
    modelAuto: '預設',
    modelFollowDefault: '跟隨預設',
    modelAutoHint: '目前知識庫設定的對話模型；不在知識庫頁面或知識庫未設定時，使用第一個可用的對話模型',
    stopGeneration: '停止生成',
    send: '傳送',
    steerRetry: '重試傳送',
    webSearchDisabledByAgent: '當前智慧代理已停用網路搜尋',
    kbLockedByAgent: '當前智慧代理已鎖定知識庫設定',
    kbDisabledByAgent: '當前智慧代理已停用知識庫功能',
    modelLockedByAgent: '當前智慧代理已鎖定模型設定',
    imageUploadDisabledByAgent: '當前智慧代理未啟用圖片上傳',
    voiceTooltip: '按住說話（{shortcut}）',
    voicePreparing: '麥克風準備中，按鈕變紅後再說話',
    voiceRecording: '正在錄音，放開結束',
    voiceReleasedEarly: '麥克風尚未就緒，請按住直到按鈕變紅再說話',
    voiceTranscribing: '正在辨識語音…',
    voiceUnsupported: '目前瀏覽器不支援錄音',
    voiceInsecureContext: '語音輸入需要透過 HTTPS 或 localhost 存取',
    voicePermissionDenied: '無法使用麥克風，請在瀏覽器中允許麥克風權限',
    voiceDeviceError: '找不到可用的麥克風',
    voiceDecodeError: '錄音處理失敗，請重試',
    voiceTranscribeFailed: '語音辨識失敗，請檢查智慧代理的 ASR 模型設定',
    voiceEmptyResult: '未辨識到語音內容',
    goToAgentSettings: '去設定智慧代理',
    hostApprovalMode: {
      ask: '請求批准',
      askHint: '刪除和工作區外的寫入都要你確認',
      auto: '替我審批',
      autoHint: '由模型代你判斷，不打擾你',
      switchFailed: '切換審批模式失敗'
    },
    messages: {
      enterContent: '請先輸入內容!',
      replying: '正在回覆中，請稍後再試!',
      steerFailed: '追加失敗，請重試',
      agentSwitchedOn: '已切換到智慧推論',
      agentSwitchedOff: '已切換到快速問答',
      agentSelected: '已選擇智慧代理「{name}」',
      webSearchNotConfigured: '未設定網路搜尋引擎，請先在設定中完成搜尋引擎選擇與介面設定。',
      webSearchEnabled: '網路搜尋已開啟',
      webSearchDisabled: '網路搜尋已關閉',
      sessionMissing: '會話 ID 不存在',
      messageMissing: '無法獲取訊息 ID，請重新整理頁面後重試',
      stopSuccess: '已停止生成',
      stopFailed: '停止失敗，請重試'
    },
    webSearch: {
      toggleOn: '開啟網路搜尋',
      toggleOff: '關閉網路搜尋',
      notConfigured: '未設定網路搜尋引擎'
    }
  },
  manualEditor: {
    defaultTitlePrefix: '新建文件',
    noDocumentKnowledgeBases: '暫無可用的文件型知識庫，請先建立一個文件型知識庫',
    actions: {
      cancel: '取消',
      saveDraft: '暫存草稿',
      publish: '發布入庫'
    },
    loading: {
      content: '正在載入內容',
      preparing: '正在準備編輯器'
    },
    status: {
      draftTag: '當前狀態：草稿',
      publishedTag: '當前狀態：已發布',
      lastUpdated: '最近更新：{time}',
      counter: '{chars} 字 · {lines} 行'
    },
    form: {
      knowledgeBasePlaceholder: '請選擇知識庫',
      titleLabel: '知識標題',
      knowledgeBaseLabel: '目標知識庫',
      titlePlaceholder: '請輸入標題',
      contentPlaceholder: '支持 Markdown 語法，可使用 # 標題、清單、程式碼塊等'
    },
    success: {
      draftSaved: '草稿已儲存',
      published: '知識已發布並開始索引'
    },
    warning: {
      selectKnowledgeBase: '請選擇目標知識庫',
      enterTitle: '請輸入知識標題',
      enterContent: '請輸入知識內容',
      contentTooShort: '內容過短，建議補充更多資訊後再發布'
    },
    error: {
      fetchDetailFailed: '獲取知識詳情失敗',
      saveFailed: '儲存失敗，請稍後重試'
    },
    labels: {
      currentKnowledgeBase: '當前知識庫'
    },
    section: {
      content: '知識內容'
    },
    title: {
      edit: '編輯 Markdown 知識',
      create: '線上編輯 Markdown 知識'
    },
    preview: {
      empty: '暫無內容'
    },
    view: {
      edit: '編輯',
      split: '分屏',
      preview: '預覽',
      splitUnavailable: '寬度不足，拖寬抽屜或全螢幕後可用分屏',
      groupLabel: '編輯區檢視'
    },
    shortcuts: {
      title: '快速鍵',
      continueList: '清單內自動續行',
      indent: '縮排 / Shift+Tab 反縮排'
    },
    toolbar: {
      bold: '粗體',
      italic: '斜體',
      strike: '刪除線',
      inlineCode: '行內程式碼',
      heading1: '一級標題',
      heading2: '二級標題',
      heading3: '三級標題',
      bulletList: '無序清單',
      orderedList: '有序清單',
      taskList: '任務清單',
      blockquote: '引用',
      codeBlock: '程式碼塊',
      link: '插入連結',
      image: '插入圖片',
      table: '插入表格',
      horizontalRule: '分割線',
      headingGroup: '標題',
      insertGroup: '插入'
    },
    table: {
      column1: '列1',
      column2: '列2',
      cell: '內容'
    },
    placeholders: {
      heading: '標題{level}',
      listItem: '清單項',
      taskItem: '任務項',
      quote: '引用內容',
      code: '程式碼內容',
      linkText: '連結文字',
      imageAlt: '描述',
      bold: '粗體文字',
      italic: '斜體文字',
      strike: '刪除線',
      inlineCode: 'code'
    },
    assistant: {
      button: '助手',
      tooltip: '讓助手幫你寫',
      continue: '續寫',
      outline: '產生大綱',
      polish: '潤飾全文',
      summarize: '總結重點',
      open: '開啟助手',
      prompts: {
        continue: '接著正文結尾續寫一段，與前文銜接。',
        outline: '根據標題和現有內容，為這篇文件擬一份結構清楚的大綱，寫在正文開頭。',
        polish: '潤飾正文：修正錯字和不通順的句子，不改變原意，分段修改。',
        summarize: '總結這篇文件的重點，在對話裡回覆，不要修改正文。'
      }
    }
  },
  file: {
    upload: '上傳檔案'
  },
  mentionDetail: {
    readOnlyFromAgent: '僅在此對話中唯讀，不顯示在知識庫清單中',
    faqCount: '共 {count} 條問答',
    kbCount: '共 {count} 個文件',
    mcpToolCount: '共 {count} 個工具',
    mcpNotSynced: '尚未同步工具',
    mcpStale: '需重新同步',
    belongsToKb: '所屬知識庫：',
    belongsToOrg: '所屬空間：',
    noCompatibleKbForAgent: '當前智慧代理的工具與作用域內知識庫的能力不比對，暫無可引用的知識庫。',
    tag: '標籤',
    searchPlaceholder: '搜尋知識庫、檔案、技能等',
    searchInGroup: '在{group}中搜尋…',
    typeToSearch: '在 {\'@\'} 後繼續輸入以搜尋…',
    viewAll: '檢視全部',
    back: '返回'
  },
  mentionBrowser: {
    browse: '按目錄瀏覽',
    path: '目錄路徑',
    root: '根目錄',
    searchFolder: '搜尋目前目錄',
    searchKb: '搜尋知識庫',
    subtree: '搜尋包含目前目錄及其子目錄。',
    wholeKb: '目前仍選取整個知識庫，選取單一檔案不會縮小範圍。',
    tags: '既有標籤仍會篩選所選檔案。',
    folderCount: '含子目錄共 {count} 個文件',
    selected: '已選取',
    deleting: '正在刪除',
    unsupported: '目前代理不支援此格式',
    forbidden: '你已無權存取此內容。',
    missing: '目錄已失效，請返回並重新選取。',
    error: '目錄載入失敗，請重試。',
    retry: '重試',
    empty: '目前檢視沒有檔案。',
    previous: '上一頁',
    next: '下一頁',
    page: '第 {page} 頁 · 共 {total} 個文件'
  },
  common: {
    confirm: '確認',
    cancel: '取消',
    fullscreen: '全螢幕',
    exitFullscreen: '退出全螢幕',
    save: '儲存',
    delete: '刪除',
    edit: '編輯',
    copy: '複製',
    copied: '已複製',
    copySuccess: '已複製',
    loading: '載入中...',
    noMoreData: '已載入全部內容',
    loadMore: '載入更多',
    error: '錯誤',
    success: '成功',
    failed: '失敗',
    selectAll: '全選',
    yes: '是',
    no: '否',
    close: '關閉',
    back: '返回',
    next: '下一步',
    finish: '完成',
    all: '全部',
    clear: '清空',
    on: '開啟',
    off: '關閉',
    confirmDelete: '確認刪除',
    deleteFailed: '刪除失敗',
    operationFailed: '操作失敗',
    file: '檔案',
    skill: '技能',
    knowledgeBase: '知識庫',
    noResult: '無結果',
    remove: '移除',
    avatar: '頭像',
    defaultUser: '使用者',
    copyFailed: '複製失敗',
    retry: '重試',
    expand: '展開',
    unsavedChanges: {
      title: '有未儲存的更改',
      body: '關閉後當前修改將丟失，確定要關閉嗎？',
      discard: '放棄更改',
      keepEditing: '繼續編輯'
    }
  },
  authStore: {
    errors: {
      parseUserFailed: '解析使用者資訊失敗',
      parseTenantFailed: '解析空間資訊失敗',
      parseKnowledgeBasesFailed: '解析知識庫清單失敗',
      parseCurrentKnowledgeBaseFailed: '解析當前知識庫失敗'
    }
  },
  auth: {
    account: '帳號',
    accountPlaceholder: '請輸入帳號',
    accountRequired: '請輸入帳號',
    accountDescription: '用於登入平台的帳號',
    login: '登入',
    logout: '退出',
    oidcLogin: '使用 OIDC 登入',
    oidcLoginWithProvider: '使用 {provider} 登入',
    redirectingToOIDC: '正在跳轉到身份提供商...',
    orContinueWith: '或使用以下方式繼續',
    oidcLoginFailed: 'OIDC 登入失敗',
    username: '使用者名',
    email: '電子信箱',
    password: '密碼',
    confirmPassword: '確認密碼',
    loginSuccessTitle: '登入成功',
    loginSuccessContent: '歡迎，你已進入 {name}',
    loggingIn: '登入中...',
    register: '註冊',
    registering: '註冊中...',
    createAccount: '建立帳戶',
    haveAccount: '已有帳戶？',
    backToLogin: '返回登入',
    loginHint: '登入以繼續使用；首次使用請在下方建立帳戶。',
    firstTime: '首次使用？',
    registerSuccess: '註冊成功，請登入',
    registerFailed: '註冊失敗',
    registerSubtitle: '建立帳戶，開始使用知識庫',
    emailPlaceholder: '輸入電子信箱地址',
    passwordPlaceholder: '輸入密碼',
    confirmPasswordPlaceholder: '再次輸入密碼',
    usernamePlaceholder: '輸入使用者名',
    emailRequired: '請輸入電子信箱地址',
    emailInvalid: '請輸入正確的電子信箱格式',
    passwordRequired: '請輸入密碼',
    passwordMinLength: '密碼至少8個字符',
    passwordMaxLength: '密碼不能超過1024個字符',
    passwordMustContainLetter: '密碼必須包含字母',
    passwordMustContainLowercaseLetter: '密碼必須包含小寫字母',
    passwordMustContainUppercaseLetter: '密碼必須包含大寫字母',
    passwordMustContainNumber: '密碼必須包含數字',
    passwordMustContainSpecialChar: '密碼必須包含特殊字符：{specialChars}',
    usernameRequired: '請輸入使用者名',
    usernameMinLength: '使用者名至少2個字符',
    usernameMaxLength: '使用者名不能超過20個字符',
    usernameInvalid: '使用者名只能包含字母、數字、底線和中文字符',
    confirmPasswordRequired: '請確認密碼',
    passwordMismatch: '兩次輸入的密碼不一致',
    loginError: '登入錯誤，請檢查帳號或密碼',
    loginErrorRetry: '登入錯誤，請稍後重試',
    registerError: '註冊錯誤，請稍後重試',
    workspaceOnboarding: {
      title: '選擇你的工作空間',
      description: '建立個人空間後即可繼續使用。',
      create: '建立空間',
      invitations: '查看邀請',
      loadingPolicy: '正在確認可用的空間加入方式…',
      policyLoadFailed: '暫時無法獲取空間權限，請檢查網路後重試。',
      retry: '重新載入',
      inviteOnlyTitle: '等待加入工作空間',
      inviteOnlyDescription: '當前系統不開放個人建立空間。你可以查看並接受管理員發來的空間邀請。',
      inviteOnlyNotice: '此帳戶只能透過邀請加入已有空間',
      help: '你現在可以建立空間，也可以稍後回來接受邀請。',
      inviteOnlyHelp: '還沒有邀請？請把你的註冊電子信箱提供給空間管理員，由管理員向你傳送邀請。'
    }
  },
  inviteRegister: {
    bannerTitle: '您被邀請加入「{tenant}」',
    bannerHint: '填寫下方資訊完成註冊，註冊成功後將自動加入該團隊。',
    bannerHintLogin: '登入後將自動加入該團隊。',
    loading: '正在驗證邀請連結…',
    invalidTitle: '邀請連結無效或已撤銷',
    invalidBody: '請聯絡邀請人重新傳送連結，或前往登入使用現有帳號。',
    backToLogin: '返回登入',
    title: '完成註冊',
    subtitle: '您被邀請加入「{tenant}」',
    email: '電子信箱',
    emailPlaceholder: 'your{\'@\'}example.com',
    emailHint: '用您自己的電子信箱註冊即可。',
    emailInvalid: '請輸入有效的電子信箱地址',
    username: '姓名',
    usernamePlaceholder: '請輸入您的姓名',
    password: '設定密碼',
    passwordPlaceholder: '至少 6 位',
    confirmPassword: '確認密碼',
    submit: '完成註冊',
    submitting: '提交中…',
    success: '註冊成功，正在進入工作空間…',
    joined: '已加入該團隊',
    failed: '註冊失敗，請稍後重試',
    usernameRequired: '請輸入姓名',
    passwordTooShort: '密碼至少 6 位',
    passwordMismatch: '兩次輸入的密碼不一致'
  },
  initialization: {
    skip: '跳過',
    next: '下一步'
  },
  graphSettings: {
    title: '知識圖譜設定',
    description: '設定實體-關係提取功能，自動從文字中抽取實體和關係建構知識圖譜（注意：這與 Wiki 知識庫中的「頁面連結圖譜」是兩回事──前者是基於 LLM 的實體-關係圖，後者是 Wiki 頁面之間的引用關係圖）',
    enableLabel: '啟用實體關係提取',
    enableDescription: '開啟後將自動從文字中提取實體和關係',
    tagsLabel: '關係類型',
    tagsDescription: '定義要提取的關係類型標籤，多個標籤用逗號分隔',
    tagsPlaceholder: '輸入關係類型，如：工作於、同事、朋友等',
    generateRandomTags: '生成隨機標籤',
    sampleTextLabel: '示例文字',
    sampleTextDescription: '用於測試實體關係提取的示例文字',
    sampleTextPlaceholder: '輸入一段包含實體和關係的文字...',
    customInstructionsLabel: '額外提取要求',
    customInstructionsDescription: '補充領域範圍、實體篩選和屬性提取要求；系統仍負責結構化輸出協議',
    customInstructionsPlaceholder: '例如：重點提取契約主體、金額、履約期限和違約責任…',
    generateRandomText: '生成隨機文字',
    entityListLabel: '實體清單',
    entityListDescription: '從文字中提取的實體及其屬性',
    nodeNamePlaceholder: '輸入實體名稱',
    attributePlaceholder: '輸入屬性值',
    addAttribute: '新增屬性',
    manageEntitiesLabel: '管理實體',
    manageEntitiesDescription: '新增或刪除實體節點',
    addEntity: '新增實體',
    relationListLabel: '關系清單',
    relationListDescription: '定義實體之間的關係連結',
    selectEntity: '選擇實體',
    selectRelationType: '選擇關係類型',
    manageRelationsLabel: '管理關係',
    manageRelationsDescription: '新增或刪除實體間的關係',
    addRelation: '新增關係',
    extractActionsLabel: '提取操作',
    extractActionsDescription: '執行實體關係提取或管理示例資料',
    startExtraction: '開始提取',
    extracting: '提取中...',
    defaultExample: '預設示例',
    clearExample: '清除示例',
    completeModelConfig: '請先完成模型設定',
    tagsGenerated: '標籤生成成功',
    tagsGenerateFailed: '標籤生成失敗',
    textGenerated: '文字生成成功',
    textGenerateFailed: '文字生成失敗',
    pleaseInputText: '請先輸入示例文字',
    extractSuccess: '實體關係提取成功',
    extractFailed: '實體關係提取失敗',
    exampleLoaded: '示例已載入',
    exampleCleared: '示例已清除',
    checkingAvailability: '正在檢查知識圖譜服務…',
    checkAvailabilityFailed: '無法檢查知識圖譜服務，請重試。',
    disabledWarning: '知識圖譜資料庫未啟用，實體關係提取功能將無法使用',
    howToEnable: '如何啟用知識圖譜？'
  },
  retrievalSettings: {
    title: '搜尋設定',
    description: '設定知識庫搜尋和訊息搜尋的全域檢索參數，參數直接透傳給 ContextDB 官方檢索介面',
    topKLabel: '檢索返回數量 (Top K)',
    topKDescription: '單次檢索返回的片段數，範圍 1–10；ContextDB 官方預設 5',
    similarityThresholdLabel: '相似度閾值',
    similarityThresholdDescription: '相關性低於該閾值的片段會被過濾，範圍 0–1；ContextDB 官方預設 0.6',
    vectorWeightLabel: '向量權重',
    vectorWeightDescription: '向量與關鍵詞混合檢索的平衡權重，範圍 0–1；ContextDB 官方預設 0.7',
    queryRewriteLabel: '查詢改寫',
    queryRewriteDescription: '檢索前由 ContextDB 用 LLM 改寫查詢以提升召回；官方預設關閉，本平台預設開啟',
    toasts: {
      saveSuccess: '檢索設定已儲存',
      saveFailed: '儲存設定失敗: {message}'
    }
  },
  defaultSettings: {
    saving: '儲存中',
    loadFailed: '預設設定載入失敗，請重試後再編輯。',
    title: '預設設定',
    readOnly: '僅空間管理員可以修改，你可以查看目前生效的預設值。',
    webSearchGroup: '網路搜尋',
    toasts: {
      saveFailed: '儲存失敗：{message}'
    },
    webSearch: {
      label: '預設搜尋引擎',
      description: '未單獨指定搜尋引擎的智慧體開啟聯網搜尋時使用。',
      unset: '未設定預設搜尋引擎，未單獨指定搜尋引擎的智慧體將無法聯網搜尋。',
      placeholder: '選擇搜尋引擎'
    },
    hints: {
      workspace: '使用空間設定。',
      system: '未設定，目前使用系統預設：{name}',
      auto: '未設定，目前自動使用第一個可用模型：{name}',
      followChat: '未設定，跟隨預設對話模型：{name}',
      staleFallback: '所選模型已刪除或不可用，目前回退到：{name}',
      staleNone: '所選模型已刪除或不可用，且沒有可回退的模型。'
    },
    slots: {
      asr: {
        label: '預設語音辨識模型',
        description: '用於影音轉寫的預設選擇。',
        none: '空間內沒有可用的語音辨識模型，影音轉寫不可用。'
      },
      vlm: {
        label: '預設視覺模型',
        description: '用於圖片理解和多模態解析的預設選擇。',
        none: '空間內沒有可用的視覺模型，圖片理解不可用。'
      },
      rerank: {
        label: '預設 Rerank 模型',
        description: '未單獨設定重排模型的檢索和內建智慧體使用。',
        none: '空間內沒有可用的 Rerank 模型，檢索將依召回順序返回。'
      },
      embedding: {
        label: '預設 Embedding 模型',
        description: '新建知識庫時預設選用。既有知識庫不受影響。',
        none: '空間內沒有可用的 Embedding 模型，無法新建知識庫。'
      },
      utility: {
        label: '輕量生成模型',
        description: '用於生成會話標題、MCP 服務使用說明等短文字任務，可選更快更便宜的模型。',
        none: '空間內沒有可用的對話模型，標題和說明生成將無法使用。'
      },
      chat: {
        label: '預設對話模型',
        description: '新建智慧體和問答預設使用，也作為背景任務的備援模型。',
        none: '空間內沒有可用的對話模型，問答和背景生成將無法使用。'
      }
    }
  },
  envVarSettings: {
    host: {
      title: '環境變數'
    }
  },
  settings: {
    modelManagement: '模型管理',
    autoCheckUpdate: '自動下載更新',
    autoCheckUpdateDesc: '開啟後自動檢查並在後台下載最新版本安裝包。',
    parserEngine: '解析引擎',
    mcpService: 'MCP服務',
    workspaceSettings: '空間設定',
    capabilityUnavailable: '當前部署不支持此功能，已返回可用頁面。',
    hostApprovalDefault: {
      title: '預設執行權限審批',
      description: '智慧體要刪除檔案，或寫入工作區以外時，用這裡決定是每次詢問你，還是由模型替你審批。新工作階段按這個開始；目前工作階段可在輸入框左側切換。'
    },
    storage: {
      title: '存儲引擎',
      engineLocal: 'Local（本地）',
      engineCos: '騰訊雲 COS',
      engineTos: '火山引擎 TOS',
      engineOss: '阿里雲 OSS'
    },
    parser: {
      title: '解析引擎'
    },
    roleDenied: {
      title: '權限不足',
      desc: '你當前的角色無權存取此設定項。請聯絡本空間的管理員獲取所需角色。'
    },
    navGroups: {
      systemAdministration: '系統管理'
    },
    skills: {
      nativeUsage: '在智能体配置中选择技能包。脚本执行需要 OpenSandbox 及相应依赖；目录可用不代表依赖已安装。',
      addSourceDescription: '导入包含唯一 SKILL.md 的技能目录，保留资料和脚本文件；只登记内容，不执行安装。',
      title: '技能管理',
      description: '管理技能包目录。选择后由官方 SkillsMiddleware 加载指令与资料；上传不会安装依赖。',
      helpTooltip: '目录保存指令、资料和脚本；脚本复制到会话沙箱运行，依赖由部署镜像提供。',
      addSkill: '新增技能',
      addStepRegister: '登記',
      addFileSelected: '已選擇 {name}',
      addClearFile: '清除',
      emptyDesc: '还没有技能包。上传 ZIP 或填写来源添加到目录。',
      deleteCatalog: '從目錄刪除',
      deleteCatalogConfirm: '确定从目录删除「{name}」？历史安装记录保留；存在历史引用时不能删除。',
      deleteSuccess: '已從目錄刪除',
      registerAccepted: '已新增到目錄',
      loadFailed: '載入失敗'
    },
    sandbox: {
      title: '沙箱設定',
      skillUploadClick: '點擊上傳 zip 壓縮包',
      skillUploadDrag: '或將檔案拖到此處',
      skillSourceSection: '從來源安裝',
      skillSourceSectionHint: '貼上 ClawHub、GitHub 或 SkillHub 連結，或 {\'@\'}owner/slug。壓縮包不超過 {size} MB。',
      skillUploadSection: '上傳本地壓縮包',
      skillUploadSectionHint: '把包含 SKILL.md 的 zip 拖到下方，或點擊選擇檔案。壓縮包不超過 {size} MB。',
      skillSourcePlaceholder: 'ClawHub 用 {\'@\'}owner/slug，GitHub / SkillHub 請貼上完整連結',
      skillSourceFailed: '從託管平台安裝技能失敗',
      skillUploadFailed: '技能上傳失敗',
      skillBundleTooLarge: '技能壓縮包不能超過 {size} MB。',
      skillBundleTooManyFiles: '技能目錄裡的檔案不能超過 {count} 個。',
      skillBundleTooManyZipEntries: '壓縮包條目不能超過 {count} 個。',
      installCommandRunning: '命令執行中',
      skillFiles: '查看檔案',
      skillFilesTitle: '檔案',
      skillFilesEmpty: '該技能還沒有可查看的檔案。',
      skillFilesLoadFailed: '載入技能檔案失敗',
      skillFilesFileLoadFailed: '無法讀取該檔案',
      skillFilesBinary: '該檔案是二進位內容，無法線上預覽。',
      skillFilesTruncated: '檔案較大，僅顯示前一部分。',
      skillFilesSelectHint: '選擇左側檔案以查看內容',
      skillFilesPreview: '預覽',
      skillFilesSource: '源碼',
      skillDisabled: '已停用技能',
      installCommandWaiting: '等待命令輸出，耗時持續更新。'
    }
  },
  agent: {
    taskLabel: '任務:',
    think: '思考',
    copy: '複製',
    addToKnowledgeBase: '新增到知識庫',
    updatePlan: '更新計劃',
    webSearchFound: '找到 <strong>{count}</strong> 個網路搜尋結果',
    toolFallback: '工具',
    stepsCompleted: '已完成 <strong>{steps}</strong> 個步驟',
    reasoningRounds: '思考 <strong>{rounds}</strong> 輪',
    earlierSteps: '已完成 {count} 個步驟',
    viewReasoning: '檢視思路',
    toolCalls: '呼叫 <strong>{tools}</strong> 次工具',
    durationSuffix: '耗時 <strong>{duration}</strong>',
    stepSummarySeparator: ' · ',
    contextCompacted: '壓縮脈絡',
    contextCompactedSummary: '{before} → {after} tokens',
    contextCompactedDegraded: '摘要不可用，已保留原始記錄',
    title: '智慧代理',
    subtitle: '設定和管理您的智慧代理，自定義對話行為和能力',
    createAgent: '建立智慧代理',
    builtin: '內建',
    disabled: '已停用',
    disable: '停用',
    enable: '啟用',
    noDescription: '暫無描述',
    selectAgent: '選擇智慧代理',
    noAgents: '暫無智慧代理',
    manageAgents: '管理',
    builtinAgents: '內建智慧代理',
    customAgents: '自定義智慧代理',
    selector: {
      title: '選擇智慧代理',
      current: '當前',
      goToSettings: '設定',
      sharedLabel: '共享',
      notReadyHint: '尚未就緒，還需設定：{items}',
      notReadyStatus: '待設定',
      configureAction: '去設定',
      sharedNotReadyContact: '請聯絡分享方管理員完成設定',
      capabilitiesSection: '能力',
      webSearchCapability: '網路搜尋',
      imageUploadCapability: '圖片上傳',
      capabilityEnabled: '開啟',
      capabilityDisabled: '關閉',
      capabilitySupported: '支持',
      capabilityUnsupported: '不支持',
      capabilityUnconfigured: '未設定'
    },
    editor: {
      assistantChanged: '助手已修改此智慧代理，請重新開啟以查看最新設定。',
      assistantDeleted: '助手已刪除此智慧代理。',
      reasoningEffortUnsupported: '當前所選模型不支持思考，除「關閉」外的選項將被忽略。',
      reasoningEffortAlwaysOn: '當前所選模型始終開啟思考，無法關閉，只能調整思考強度。',
      createTitle: '建立智慧代理',
      editTitle: '編輯智慧代理',
      basicInfo: '基本資訊',
      basicInfoDesc: '設定智慧代理的名稱、描述與運行模式',
      promptsConfig: '提示語',
      promptsConfigDesc: '設定系統提示語、脈絡模板、意圖/改寫/兜底提示語',
      modelConfig: '模型設定',
      modelConfigDesc: '設定對話模型、ReRank 等輔助模型及生成參數',
      toolsConfig: '工具設定',
      toolsConfigDesc: '設定 Agent 可以使用的工具',
      knowledgeConfig: '知識庫',
      knowledgeConfigDesc: '設定智慧代理可存取的知識庫範圍與 FAQ 策略',
      agentId: '智慧代理 ID',
      agentIdDesc: 'API 集成時可使用此 ID 指定智慧代理',
      name: '名稱',
      namePlaceholder: '請輸入智慧代理名稱',
      nameRequired: '請輸入智慧代理名稱',
      systemPromptRequired: '請輸入系統提示語',
      modelRequired: '請選擇模型',
      queryMissingInRewrite: '改寫使用者提示語必須包含 {\'{{\'}query{\'}}\'} 預留位置',
      queryMissingInFallback: '兜底提示語必須包含 {\'{{\'}query{\'}}\'} 預留位置',
      description: '描述',
      descriptionPlaceholder: '請輸入智慧代理描述',
      normalDesc: '快速回應，直接回答問題',
      agentDesc: '多步思考，深度分析複雜問題',
      model: '模型',
      modelPlaceholder: '請選擇模型',
      systemPrompt: '系統提示語',
      systemPromptPlaceholder: '自定義系統提示語，定義智慧代理的行為和角色（使用 {\'{{\'}web_search_status{\'}}\'} 預留位置動態控制網路搜尋行為）',
      contextTemplateRequired: '請輸入脈絡模板',
      temperature: '溫度',
      thinking: '思考模式',
      citationEnabled: '輸出來源引用',
      citationEnabledDesc: '在最終回答中展示知識庫和網頁來源；關閉後仍會正常檢索和使用證據',
      mode: '運行模式',
      knowledgeBases: '關聯知識庫',
      allKnowledgeBases: '全部知識庫',
      selectedKnowledgeBases: '指定知識庫',
      noKnowledgeBase: '不使用知識庫',
      selectKnowledgeBases: '選擇知識庫',
      selectKnowledgeBasesDesc: '選擇要關聯的知識庫（包括協作知識庫）',
      myKnowledgeBases: '我的知識庫',
      sharedKnowledgeBases: '協作知識庫',
      retrieveKBOnlyWhenMentioned: '僅在 {\'@\'} 提及時檢索',
      retrieveKBOnlyWhenMentionedDesc: '關閉：自動檢索已設定的知識庫，開啟：僅當使用者 {\'@\'} 提及時才檢索',
      rerankModel: 'ReRank 模型',
      rerankModelDesc: '用於對知識庫檢索結果進行重排序，提高回答準確性',
      rerankModelPlaceholder: '請選擇 ReRank 模型',
      rerankModelOptionalHint: '當前作用域內暫無 RAG 類型知識庫，可不填；後續若加入 RAG 知識庫，將自動使用空間預設重排模型，仍建議顯式設定。',
      maxIterations: '主 Agent 單輪模型呼叫上限',
      maxIterationsLimit: '限制',
      maxIterationsUnlimited: '不限制',
      allowedTools: '允許的工具',
      retrievalStrategy: '檢索策略',
      contextTemplate: '脈絡模板',
      contextTemplatePlaceholder: '自定義脈絡模板...',
      queryUnderstandModel: '問題理解模型',
      queryUnderstandModelPlaceholder: '留空則復用主對話模型',
      rewritePromptSystem: '改寫系統提示語',
      rewritePromptSystemPlaceholder: '留空使用系統預設提示語',
      rewritePromptUser: '改寫使用者提示語',
      rewritePromptUserPlaceholder: '留空使用系統預設提示語',
      maxCompletionTokens: '最大生成Token數',
      maxCompletionTokensDefault: '預設',
      maxCompletionTokensCustom: '自定義',
      fallbackStrategy: '兜底策略',
      fallbackResponse: '固定回覆內容',
      fallbackResponsePlaceholder: '抱歉，我無法回答這個問題。',
      fallbackPrompt: '兜底提示語',
      fallbackPromptPlaceholder: '留空使用系統預設提示語',
      skillsConfig: '技能',
      skillsSelection: '技能清單',
      skillsAll: '全部',
      skillsSelected: '指定',
      skillsNone: '停用',
      skillsGroupUnavailable: '不可用',
      noSkillsAvailable: '空間目錄裡還沒有技能。',
      goSandboxSettings: '管理沙箱',
      sandboxBackend: '運行沙箱',
      memoryEnabled: '長期記憶',
      nativeRuntime: {
        adoptRuntime: '採用目前執行設定',
        incompatible: '目前設定含有與此部署執行策略不相容的值。請先核對下列變動，採用後僅修改草稿，儲存後生效。',
        adoptQuick: '採用目前原生快速問答設定',
        changesPending: '以下變動已套用至草稿，儲存後生效。',
        removed: '移除此欄位',
        defaultsUnavailable: '無法取得目前執行預設設定，暫時無法儲存。請重新載入。',
        retry: '重新載入',
        resolveBeforeSave: '請先處理不相容設定，再儲存。',
        quickDesc: '快速問答透過原生 Agent 按需檢索與回答，使用獨立的模型呼叫次數上限。',
        promptDesc: '設定目前模式使用的系統提示詞或範本參照'
      },
      postCreateHint: {
        title: '建立成功',
        footer: '可繼續調整設定，設定共享與發布通路，完成後點擊「儲存並關閉」。'
      },
      buttons: {
        create: '建立智慧代理',
        saveAndClose: '儲存並關閉'
      }
    },
    messages: {
      created: '已建立智慧代理',
      updated: '智慧代理已更新',
      deleted: '智慧代理已刪除',
      deleteFailed: '刪除失敗',
      saveFailed: '儲存失敗',
      copied: '已複製智慧代理',
      copyFailed: '複製失敗',
      disabled: '已停用',
      enabled: '已啟用'
    },
    delete: {
      confirmTitle: '刪除智慧代理',
      confirmMessage: '確定要刪除智慧代理「{name}」嗎？此操作不可復原。'
    },
    shareScope: {
      title: '共享範圍說明',
      desc: '空間成員以唯讀方式使用該智慧代理，將遵循您當前設定的能力與資源；您對智慧代理的修改會同步給已共享的空間。如需允許空間成員編輯知識庫內容，請將知識庫共享到空間。',
      knowledgeBase: '知識庫',
      chatModel: '對話模型',
      rerankModel: '重排模型',
      webSearch: '網路搜尋',
      mcp: 'MCP 服務',
      kbAll: '全部知識庫',
      kbSelected: '指定 {count} 個知識庫',
      kbNone: '不使用',
      modelConfigured: '已設定',
      modelNotSet: '未設定',
      enabled: '開啟',
      disabled: '關閉',
      mcpAll: '全部服務',
      mcpSelected: '指定 {count} 個服務',
      mcpNone: '不使用'
    },
    detail: {
      title: '智慧代理詳情',
      useInChat: '在對話中使用'
    },
    empty: {
      title: '暫無自定義智慧代理',
      description: '點擊右上角按鈕建立您的第一個智慧代理',
      sharedTitle: '暫無共享智慧代理',
      sharedDescription: '您可以加入空間或請求他人將智慧代理共享給您',
      favoritesTitle: '暫無收藏',
      favoritesDescription: '在智慧代理卡片右上角點擊星標即可收藏',
      recentsTitle: '暫無最近存取',
      recentsDescription: '最近使用過的智慧代理會出現在這裡'
    },
    sections: {
      builtin: '內建',
      mine: '我建立的',
      tenantOthers: '本空間 · 其他成員',
      tenantReadonly: '本空間 · 僅查看',
      sharedByMe: '我共享的',
      sharedEditable: '共享給我 · 可編輯',
      sharedReadonly: '共享給我 · 僅查看'
    },
    tabs: {
      sharedToMe: '共享給我'
    },
    features: {
      webSearch: '支持網路搜尋',
      knowledgeBase: '關聯知識庫',
      mcp: '支持MCP服務',
      multiTurn: '多輪對話'
    },
    mode: {
      normal: '快速問答',
      agent: '智慧推論'
    },
    type: {
      normal: '快速問答',
      agent: '智慧推論'
    },
    capabilities: {
      kbCount: '指定 {count} 個知識庫',
      kbAll: '可存取全部知識庫',
      mcpEnabled: '啟用 MCP 服務',
      multiTurn: '多輪對話'
    },
    artifactDrawer: {
      buttonTitle: '查看本次生成的檔案',
      title: '生成的檔案',
      empty: '本次未生成可下載的檔案',
      preview: '預覽',
      previewBack: '返回清單',
      collecting: '正在儲存生成的檔案…',
      delete: '刪除',
      deleteTitle: '刪除這個檔案？',
      deleteConfirm: '將永久刪除「{name}」，包括已儲存的檔案內容，且無法復原。',
      deleted: '檔案已刪除',
      deleteFailed: '刪除失敗，請稍後重試',
      download: '下載',
      downloadFailed: '下載失敗，請稍後重試',
      inlinePreviewHint: '點擊預覽',
      inlineMissing: '檔案不可用',
      inlineDeleted: '檔案已刪除'
    }
  },
  knowledgeStages: {
    expandBranch: '展開子項',
    collapseBranch: '收起子項',
    resizeDrawer: '拖曳調整面板寬度',
    status: {
      pending: '等待中',
      running: '進行中',
      finalizing: '最佳化中',
      done: '已完成',
      failed: '失敗',
      skipped: '已跳過',
      cancelled: '已取消'
    },
    stage: {
      docreader: '文件解析',
      chunking: '切塊',
      embedding: '向量化',
      multimodal: '多模態識別',
      postprocess: '後處理'
    },
    stall: {
      title: '已 {minutes} 分鐘沒有進展，可能已卡住'
    },
    processConfig: {
      title: '本次解析設定'
    }
  },
  uploadConfirm: {
    imageEmbeddingModel: '圖像索引 Embedding 模型',
    imageIndexInherited: '圖像索引使用知識庫綁定的 Embedding 模型；如需更換，請前往知識庫設定。',
    imageVectorIndex: '本次圖片向量索引',
    imageVectorIndexHint: '為本次上傳或重新解析的圖片產生向量，不改變知識庫預設設定。是否參與檢索仍由知識庫的「圖片向量檢索」開關決定。',
    imageVectorRequiresIndex: '請先在知識庫設定中開啟向量索引。',
    documentSummary: '文件摘要',
    documentSummaryDescription: '為本次匯入的文件選擇是否自動生成摘要。',
    generateSummary: '生成文件摘要',
    generateSummaryHint: '預設開啟。關閉後跳過摘要生成，文件解析、索引及其他處理步驟仍按設定執行。',
    title: '上傳文件確認',
    parseConfig: '解析設定',
    configNav: '解析設定導航',
    navParserDefault: '預設',
    navParserCustomized: '已自定義',
    moreOptions: '更多處理選項',
    summaryParentChildShort: '父子切塊',
    summaryParserForceScanned: '掃描件解析',
    summaryQuestionCountValue: '{count} 個',
    summaryGraphTagsValue: '{count} 個',
    navChunkingSummary: '切塊 {size}',
    statusOn: '已開啟',
    statusOff: '未開啟',
    notSet: '未設定',
    summaryNoTags: '未設定',
    summaryTagsCount: '{count} 個標籤',
    confirm: '確認上傳並解析',
    cancel: '取消',
    tabTags: '文件標籤',
    tagsDescription: '為本批次匯入的所有文件選擇標籤，可多選',
    tagsPlaceholder: '請選擇標籤（可多選）',
    tagsEmpty: '當前知識庫暫無標籤，可上傳後在標籤管理中建立',
    tagsLoadFailed: '標籤載入失敗，可稍後在文件清單中設定',
    noItems: '請至少新增一個檔案或 URL',
    urlItemLabel: 'URL',
    urlAdded: '已新增 URL',
    urlDuplicate: '該 URL 已在清單中',
    statusNeedsSetup: '待設定',
    multimodalSetupHint: '含圖片內容，請啟用多模態並選擇模型',
    asrSetupHint: '含音訊內容，請啟用語音辨識並選擇模型',
    vlmModelRequired: '請設定多模態模型',
    asrModelRequired: '請設定語音辨識模型',
    vlmModelSelectRequired: '已啟用多模態，請選擇 VLM 模型',
    asrModelSelectRequired: '已啟用語音辨識，請選擇 ASR 模型',
    continueAdd: '繼續新增',
    destinationLabel: '上傳位置',
    destinationChange: '更改上傳位置',
    filesAdded: '已新增 {count} 個檔案',
    filesAllDuplicate: '所選檔案已在清單中',
    titleManual: '線上編輯發布確認',
    confirmManual: '確認發布並解析',
    titleReparse: '重新解析確認',
    confirmReparse: '確認並重新解析',
    reparseSource: '待重新解析文件',
    reparseHint: '將沿用上次解析的設定，可在此調整',
    manualCharCount: '{count} 個字符',
    pdfForceScanned: {
      label: '按掃描件解析 PDF',
      description: '適用於網頁列印、掃描件、圖片型 PDF。開啟後會逐頁 OCR，解析更完整但耗時和模型呼叫更多。'
    }
  },
  knowledgeBase: {
    videosFilteredNoVLM: '已跳過 {count} 個影片檔案（暫不支持影片上傳）',
    importURL: '匯入網頁',
    addDocument: '新增文件',
    importURLTitle: '匯入網頁',
    urlRequired: '請輸入URL',
    invalidURL: '請輸入有效的URL',
    urlLabel: 'URL地址',
    urlPlaceholder: '請輸入網頁URL，例如：https://example.com',
    urlTip: '支持匯入各類網頁內容，系統會自動提取和解析網頁中的文字內容',
    channelLabel: '來源通路',
    channelWeb: '網頁端',
    channelApi: 'API',
    channelBrowserExtension: '瀏覽器外掛',
    channelWechat: '微信',
    channelWecom: '企業微信',
    channelFeishu: '飛書',
    channelDingtalk: '釘釘',
    channelSlack: 'Slack',
    channelIm: 'IM 通路',
    channelConfluence: 'Confluence',
    channelGitLab: 'GitLab',
    channelNextcloud: 'Nextcloud',
    channelSeafile: 'Seafile',
    channelIma: '騰訊 IMA',
    channelUnknown: '未知',
    selectedCount: '已選 {count} 項',
    pdfDocFormat: 'pdf、doc 格式檔案，不超過{size}M',
    textMarkdownFormat: 'text、markdown格式檔案，不超過{size}M',
    dragFileNotText: '請拖曳檔案而不是文字或連結',
    searchPlaceholder: '搜尋知識庫...',
    noMatch: '未找到比對的知識庫',
    noKnowledge: '暫無可用知識庫',
    loadingFailed: '載入知識庫失敗',
    allFilesSkippedNoEngine: '所選檔案類型暫無可用解析引擎，已全部跳過',
    filesSkippedNoEngine: '{count} 個檔案因無可用解析引擎被跳過',
    moveToFolder: {
      action: '移動到目錄',
      newFolderPlaceholder: '輸入新目錄名稱',
      newFolderAddRoot: '在根目錄下新建子目錄',
      newFolderAddUnder: '在「{folder}」下新建子目錄',
      duplicate: '該目錄已存在'
    },
    folderTree: {
      title: '目錄',
      rootRow: '根目錄'
    },
    sort: {
      title: '排序'
    },
    infoCard: {
      title: '知識庫資訊'
    }
  },
  resourceOrigin: {
    mine: '我建立',
    mineTooltip: '由當前使用者建立',
    tenant: '本空間',
    tenantTooltip: '本空間其他成員建立',
    tenantTooltipWithCreator: '由 {creator} 建立',
    space: '共享空間',
    spaceTooltip: '來自共享空間「{space}」',
    spaceTooltipWithTenant: '來自共享空間「{space}」· 源空間 {tenant}',
    shared: '外部共享',
    sharedTooltip: '透過共享空間從其他空間存取'
  },
  listSpaceSidebar: {
    all: '全部',
    workspace: '本空間',
    spaces: '共享給我',
    favorites: '收藏',
    recents: '最近'
  },
  batchManage: {
    selectAll: '全選',
    cancel: '取消',
    delete: '刪除對話',
    deleteConfirmTitle: '刪除對話',
    deleteConfirmBody: '確定要刪除選中的 {count} 條對話嗎？刪除後無法復原。',
    deleteAllConfirmBody: '確定要刪除所有對話嗎？此操作無法復原。',
    deleteSuccess: '已刪除',
    deleteFailed: '刪除失敗，請稍後再試'
  },
  contextualGuide: {
    stepOf: '{current} / {total}',
    skip: '跳過',
    prev: '上一步',
    next: '下一步',
    done: '知道了',
    interactHint: '請直接點擊標示區域繼續',
    chat: {
      steps: {
        done: {
          title: '開始探索吧',
          desc: '試試提一個與已上傳文件相關的問題，體驗帶引用的精準回答。'
        },
        send: {
          title: '傳送開始對話',
          desc: '傳送後將建立新會話，AI 會結合知識庫內容作答，並標註引用片段。'
        },
        input: {
          title: '輸入你的問題',
          desc: '直接描述你想了解的內容；也可點擊上方推薦問題快速開始。'
        },
        kb: {
          title: '選擇知識範圍',
          desc: '點擊 {\'@\'} 可指定一個或多個知識庫/檔案，僅基於選中內容回答；不選則按當前智慧代理設定檢索。'
        }
      }
    },
    kbDetail: {
      steps: {
        done: {
          title: '解析完成後即可使用',
          desc: '文件解析入庫後，可在對話中 {\'@\'} 本知識庫提問，回答會附帶引用來源。'
        },
        upload: {
          title: '新增文件',
          desc: '點擊此處上傳檔案、資料夾，或匯入網頁與線上編輯內容。'
        },
        intro: {
          title: '知識庫還是空的',
          desc: '新增第一份資料後，才能基於它進行檢索與對話。支持拖曳上傳多種文件格式。'
        }
      }
    },
    agentCreate: {
      steps: {
        submit: {
          title: '儲存智慧代理',
          desc: '確認設定後點擊標示的「確定」完成建立，即可在對話中選擇該智慧代理。'
        },
        navTools: {
          title: '工具與 MCP（可選）',
          desc: '智慧推論模式下可勾選內建工具、MCP 服務等，擴展搜尋、計算等能力。'
        },
        multimodal: {
          title: '啟用附件上傳',
          desc: '可分別設定圖片、音訊上傳及附件解析策略；啟用圖片上傳時需在下方選擇 VLM 模型。'
        },
        navMultimodal: {
          title: '附件上傳（可選）',
          desc: '開啟後，對話中可上傳圖片、文件、音訊等附件；圖片理解需先在系統設定中設定 VLLM 模型。'
        },
        navWebsearch: {
          title: '聯網搜尋（可選）',
          desc: '設定是否允許智慧代理呼叫外部搜尋引擎補充實時資訊。'
        },
        knowledge: {
          title: '知識庫範圍',
          desc: '「全部」適合通用助手；「指定」可限定專業領域；「不關聯」則僅依賴模型自身能力或聯網搜尋。'
        },
        navKnowledge: {
          title: '關聯知識庫',
          desc: '決定智慧代理可檢索哪些知識。預設「全部知識庫」，也可改為指定庫或暫不關聯。'
        },
        model: {
          title: '選擇模型',
          desc: '從下拉清單選擇已設定的對話模型；沒有合適模型時請先到系統設定新增。'
        },
        navModel: {
          title: '綁定對話模型',
          desc: '每個智慧代理必須指定一個 KnowledgeQA 模型作為推論引擎。'
        },
        name: {
          title: '命名與描述',
          desc: '取一個易識別的名稱。智慧推論模式下系統可能已預填預設名稱，可按需修改。'
        },
        agentType: {
          title: '選擇智慧代理類型',
          desc: '預設類型會自動填充系統提示語、推薦工具與知識庫範圍（如 Wiki 建構、資料分析等）。可按情境切換，名稱與描述會隨之更新。'
        },
        mode: {
          title: '選擇運行模式',
          desc: '「普通模式」適合固定流程的快速問答；「智慧推論」可呼叫工具、多步思考，適合複雜任務。'
        }
      }
    },
    agentList: {
      steps: {
        create: {
          title: '建立你的智慧代理',
          desc: '智慧代理把模型、知識庫、工具與提示語組合成可復用的對話助手。點擊下方標示的「建立智慧代理」開始設定。'
        }
      }
    },
    kbCreate: {
      steps: {
        submit: {
          title: '建立知識庫',
          desc: '點擊「知道了」結束引導，無需現在建立知識庫。準備好後，填寫名稱、確認類型與模型，再點擊「建立」。'
        },
        faq: {
          title: 'FAQ 索引方式',
          desc: '設定問答對的索引模式。建立後可在本頁繼續新增 FAQ 條目。'
        },
        multimodalVllm: {
          title: '選擇 VLM 模型',
          desc: '開啟多模態後需指定 VLM（視覺語言模型）。若清單為空，請先在系統設定中新增 VLLM 類型模型。'
        },
        multimodalToggle: {
          title: '開啟多模態解析',
          desc: '啟用後，上傳的圖片類文件將使用視覺語言模型提取內容，便於檢索與問答。'
        },
        navMultimodal: {
          title: '多模態 / 圖片理解（可選）',
          desc: '若文件含大量圖表、掃描件或需理解圖片內容，可在此開啟多模態並選擇 VLM 模型。'
        },
        storage: {
          title: '存儲引擎（可選）',
          desc: '原始檔案存放位置（本地或物件存儲）。預設跟隨空間設定即可。'
        },
        chunking: {
          title: '切塊策略（可選）',
          desc: '決定文件如何切分為檢索片段。預設切塊大小已針對 RAG 最佳化，一般無需修改。'
        },
        parser: {
          title: '解析引擎（可選）',
          desc: '控制 PDF、Office 等檔案的解析方式。預設設定適用於大多數情境，有 OCR 需求時可在此調整。'
        },
        embedding: {
          title: 'Embedding 模型',
          desc: '將文字轉為向量以支持語義檢索。與上方索引策略中的「向量/關鍵字檢索」配合使用。'
        },
        llm: {
          title: '對話 / 摘要模型',
          desc: '用於文件摘要、問答生成等。若清單為空，請透過下拉選單前往系統設定新增模型。'
        },
        navModels: {
          title: '設定模型（必填）',
          desc: '知識庫必須綁定對話模型；開啟檢索時還需 Embedding 模型。點擊左側「模型設定」進入。'
        },
        indexing: {
          title: '選擇索引能力',
          desc: '預設已開啟向量與關鍵字檢索，可按需開啟 Wiki 結構化索引或知識圖譜。至少保留一種檢索方式。'
        },
        name: {
          title: '填寫名稱',
          desc: '取一個便於識別的名稱，例如「產品手冊」或「客服 FAQ」。描述可選填。'
        },
        type: {
          title: '選擇知識庫類型',
          desc: '文件庫適合上傳 PDF、Word 等檔案；FAQ 庫適合問答對。建立後類型不可更改，請按需選擇。'
        }
      }
    },
    tenantModels: {
      needChatModelFirst: '請先新增對話模型（KnowledgeQA），再建立智慧代理。',
      stepsAgent: {
        done: {
          title: '然後建立智慧代理',
          desc: '儲存並關閉設定後，點擊「建立智慧代理」，嚮導會帶你設定模式、知識庫與附件上傳等選項。'
        },
        addModel: {
          title: '新增對話模型',
          desc: '點擊「新增模型」，選擇 KnowledgeQA 類型並填寫接入資訊。'
        },
        intro: {
          title: '需要先設定對話模型',
          desc: '建立智慧代理至少需要一種 KnowledgeQA（對話）模型。請先在系統設定中新增；Embedding 模型僅建立知識庫時需要。'
        }
      },
      steps: {
        done: {
          title: '新增完成後繼續',
          desc: '模型儲存後關閉設定頁，即可點擊「新建知識庫」；建立嚮導會引導你完成類型、索引與模型綁定。'
        },
        addModel: {
          title: '新增模型',
          desc: '點擊「新增模型」，分別設定 KnowledgeQA（對話）與 Embedding 類型。Lite 使用者可使用 Ollama 拉取本地模型。'
        },
        intro: {
          title: '需要先設定模型',
          desc: '建立文件知識庫至少需要：一個對話模型（用於摘要與問答）和一個 Embedding 模型（用於向量檢索）。請先在系統設定中新增。'
        }
      }
    },
    kbList: {
      steps: {
        create: {
          title: '建立第一個知識庫',
          desc: '知識庫用來存放文件與 FAQ。點擊下方標示的「新建知識庫」按鈕，我們會帶你完成表單填寫。'
        }
      }
    }
  },
  newUserGuide: {
    stepOf: '{current} / {total}',
    skip: '跳過引導',
    prev: '上一步',
    next: '下一步',
    done: '完成',
    reopen: '新手引導',
    steps: {
      done: {
        title: '一切就緒',
        desc: '你已經了解了核心功能，現在就開始建構你的知識助手吧！隨時可點擊選單頂部暱稱旁的幫助按鈕重新查看引導。'
      },
      models: {
        title: '設定你的模型',
        desc: '這是關鍵一步：在模型管理中新增對話、向量等模型，知識庫與對話功能才能正常工作。點擊「新增模型」即可開始設定。'
      },
      settings: {
        title: '帳戶與設定入口',
        desc: '點開這裡可以管理帳戶、成員與系統設定。需要再次查看本引導時，可點擊選單頂部暱稱旁的幫助按鈕重新打開。'
      },
      agents: {
        title: '打造專屬智慧代理',
        desc: '把知識庫、提示語與工具組合成可復用的智慧代理，沉澱你的專業能力。'
      },
      chat: {
        title: '發起智慧對話',
        desc: '基於知識庫內容向 AI 提問，獲得帶引用來源的精準回答。點擊這裡開始新對話。'
      },
      knowledge: {
        title: '建立你的知識庫',
        desc: '知識庫是一切的起點：上傳文件、網頁或 FAQ，小知會自動解析並建立索引。點擊這裡進入知識庫。'
      },
      welcome: {
        title: '歡迎使用小知',
        desc: '只需幾步，帶你快速了解知識庫、對話與智慧代理的核心用法。點擊「下一步」開始。'
      },
      assistant: {
        title: '認識小知助手',
        desc: '可以詢問小知的版本、功能與設定，也可以結合目前頁面，以你的身分建立智慧代理、設定定時任務或整理知識。'
      }
    }
  },
  assistantEntryGuide: {
    stepOf: 'v0.9.0 新功能',
    skip: '知道了',
    interactHint: '點擊反白的入口，開啟助手試試。'
  },
  chatHeader: {
    automationTask: '自動化',
    moreActions: '更多對話操作',
    toggleSandboxPanel: '沙箱終端',
    copyMarkdown: '複製為 Markdown',
    deleteSession: '刪除對話',
    renamePlaceholder: '輸入對話標題',
    temporaryWorkspace: '臨時工作區',
    markdownCopied: '完整對話已複製為 Markdown',
    markdownCopyFailed: '複製 Markdown 失敗，請稍後重試',
    clearConfirmTitle: '清空對話訊息',
    clearConfirmBody: '確認清空當前對話的全部訊息？對話本身會保留，此操作無法復原。',
    deleteConfirmTitle: '刪除對話',
    deleteConfirmBody: '確認刪除當前對話？刪除後將無法復原。',
    deleteSuccess: '對話已刪除',
    markdown: {
      sessionId: '會話 ID',
      exportedAt: '匯出時間',
      user: '使用者',
      assistant: '助手',
      attachments: '附件',
      references: '引用'
    },
    grants: {
      menu: '已允許的操作',
      description: '本對話中已允許、不再詢問的操作。撤銷後再次呼叫時會重新詢問。',
      empty: '暫無已允許的操作',
      revoke: '撤銷',
      revoked: '已撤銷',
      revokeFailed: '撤銷失敗',
      loadFailed: '載入失敗'
    }
  },
  menu: {
    sessionInProgress: '會話進行中',
    sessionUnread: '有新回覆',
    knowledgeBase: '知識庫',
    agents: '智慧代理',
    automations: '自動化',
    artifacts: '產物',
    organizations: '共享空間',
    newChat: '新對話',
    settings: '系統設定',
    logout: '登出',
    clearMessages: '清空訊息',
    clearMessagesSuccess: '訊息已清空',
    clearMessagesFailed: '清空訊息失敗，請稍後再試',
    renameSession: '修改標題',
    renameSessionSuccess: '標題已更新',
    renameSessionFailed: '修改標題失敗，請稍後再試',
    batchManage: '批次管理',
    newSession: '新會話',
    pin: '置頂',
    unpin: '取消置頂',
    pinFailed: '置頂失敗，請稍後再試',
    unpinFailed: '取消置頂失敗，請稍後再試',
    search: '搜尋',
    collapseSidebar: '收起側邊欄',
    expandSidebar: '展開側邊欄',
    myChats: '我的對話',
    apiChats: 'API 會話',
    noSessions: '暫無對話'
  },
  resourceSort: {
    title: '排序',
    updatedTime: '更新時間',
    updatedTimeDescription: '預設選項。',
    createdTime: '建立時間',
    createdTimeDescription: '查看最新或最早建立的內容',
    name: '名稱',
    nameDescription: '快速尋找明確知道名稱的內容',
    recentlyUpdated: '最近更新',
    earliestUpdated: '最早更新',
    recentlyCreated: '最近建立',
    earliestCreated: '最早建立',
    nameAscending: 'A–Z',
    nameDescending: 'Z–A'
  },
  artifactLibrary: {
    title: '產物',
    subtitle: '智慧代理在各個會話中生成的檔案，都會匯總在這裡',
    typeFilter: '按類型篩選',
    searchPlaceholder: '搜尋檔名',
    total: '共 {count} 個檔案',
    versions: '{count} 個版本',
    preview: '預覽',
    delete: '刪除',
    deleteTitle: '刪除這個檔案？',
    deleteConfirm: '將永久刪除「{name}」，包括已儲存的檔案內容，且無法復原。',
    deleteConfirmVersions: '將永久刪除「{name}」的全部 {count} 個版本，包括已儲存的檔案內容，且無法復原。',
    deleted: '檔案已刪除',
    deleteFailed: '刪除失敗，請稍後重試',
    download: '下載',
    downloadFailed: '下載失敗，請稍後重試',
    openSession: '打開所在會話',
    untitledSession: '未命名會話',
    loadMore: '載入更多',
    loadFailed: '產物載入失敗',
    retry: '重試',
    clearFilters: '清除篩選',
    noMatches: {
      title: '沒有比對的檔案',
      description: '換個關鍵字或檔案類型試試'
    },
    empty: {
      title: '還沒有產物',
      description: '在對話中讓智慧代理生成報告、表格或簡報，檔案會出現在這裡'
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
      document: '文件',
      spreadsheet: '表格',
      presentation: '簡報',
      image: '圖片',
      web: '網頁',
      data: '資料'
    }
  },
  localBrowser: {
    pipOpen: '彈出懸浮窗',
    pipReturn: '返回對話小窗',
    pipFailed: '無法打開懸浮窗，請重試。',
    captureScreenshot: '截取網頁畫面',
    navigationIncomplete: '導航未達到目標載入階段，請檢查當前頁面。',
    noEntries: '沒有返回記錄。',
    stopping: '正在結束任務…',
    elapsedSeconds: '{seconds} 秒',
    searchInstructionsTitle: '瀏覽器搜尋指令',
    searchInstructionsDescription: '設定你偏好的搜尋引擎和搜尋地址。',
    searchInstructionsHint: '儲存後下次請求生效，留空使用預設指令。',
    searchInstructionsReset: '復原預設',
    searchInstructionsSaved: '已儲存',
    sourceHint: '本輪使用本機瀏覽器查詢和操作網頁，可與聯網搜尋、知識庫及其他工具配合使用。',
    pressKey: '按鍵',
    hoverPage: '懸停元素',
    scrollPage: '滾動頁面',
    focusElement: '聚焦元素',
    blurElement: '移開焦點',
    selectOption: '選擇選項',
    closeTab: '關閉分頁',
    runScript: '執行網頁指令碼',
    readConsole: '查看控制台',
    readNetwork: '查看網路請求',
    resizeWindow: '調整視窗大小',
    emulateDevice: '模擬裝置',
    actionPending: '正在操作瀏覽器…',
    actionRecorded: '已記錄瀏覽器操作',
    untitledTab: '未命名分頁',
    contentTruncated: '僅顯示部分網頁內容。',
    controlScope: '僅控制本對話的瀏覽器操作',
    pauseHint: '中斷當前瀏覽器操作並保留頁面，可繼續操作；不會停止整段對話。',
    stopHint: '關閉本任務新建的分頁，歸還借用的分頁；不會關閉瀏覽器或撤銷配對。',
    openPage: '打開網頁',
    switchPage: '切換網頁',
    readPage: '查看網頁',
    listTabs: '查看分頁',
    clickPage: '點擊元素',
    fillPage: '填寫內容',
    waitPage: '等待頁面',
    openTab: '新建任務標籤',
    switchTab: '切換任務標籤',
    authorizeTab: '請求標籤授權',
    returnTab: '歸還標籤',
    needHelp: '等待你操作',
    browserAction: '瀏覽器操作',
    actionFailed: '未完成',
    actionCompleted: '操作已完成',
    commandBusy: '上一條瀏覽器操作尚未結束，請等待完成後繼續。',
    invalidArguments: '瀏覽器工具參數格式錯誤或不完整，智慧代理需要修正後再執行。',
    commandInterrupted: '瀏覽器操作已中斷，請先確認頁面狀態，再從小預覽繼續任務。',
    actionFailedHint: '瀏覽器操作未完成，請檢查當前頁面後重試。',
    previewStale: '畫面暫未更新',
    previewIdle: '已保留最後畫面',
    previewLive: '畫面同步中',
    previewLoading: '正在獲取畫面',
    borrowHint: '請切換到要借用的網頁，在 BrowserSkill 授權提示中選擇「允許」或「拒絕」。授權透過後會自動繼續；「繼續操作」只復原暫停的任務，不代替借用授權。',
    helpHint: '點擊預覽前往瀏覽器，完成上述步驟後，在瀏覽器幫助提示中確認完成。',
    settingsTitle: '瀏覽器連結',
    settingsDescription: '透過 BrowserSkill 連結本機 Chrome 或 Edge，配對後即可在對話中操作真實網頁。',
    openSettings: '前往瀏覽器連結',
    settingsHint: '在工具箱中連結 BrowserSkill，即可在對話裡使用本機瀏覽器。',
    unavailable: '伺服器端尚未啟用本機瀏覽器，請聯絡管理員。',
    source: '瀏覽器來源',
    sandbox: '沙箱瀏覽器',
    local: '本機瀏覽器',
    paused: '已暫停',
    connected: '已連結',
    disconnected: '未連結',
    resume: '繼續操作',
    pause: '暫停操作',
    start: '開始任務',
    stop: '結束瀏覽器任務',
    resumeShort: '繼續',
    pauseShort: '暫停',
    stopShort: '結束',
    pairHint: '打開擴展的「連結設定 → 遠程連結」，貼上配對連結並確認伺服器。連結 5 分鐘內有效，僅可使用一次。',
    copyPairing: '複製配對連結',
    copied: '已複製',
    windowHint: '任務在獨立的瀏覽器任務視窗中運行。借用已有分頁需要你的授權。',
    preview: '本機瀏覽器任務預覽',
    waiting: '等待任務頁面',
    startHint: '發起瀏覽器請求後，會建立獨立的任務視窗。',
    revoke: '撤銷裝置授權',
    revokeConfirm: '撤銷後需要重新配對，才能繼續使用本機瀏覽器。',
    failed: '操作失敗，請重試',
    productDescription: '開源的 Chrome / Edge 擴展，讓智慧代理在你的瀏覽器裡打開網頁、讀取內容並完成操作。',
    offline: '離線',
    notPaired: '未配對',
    lastSeen: '最近連結',
    readyHint: '已準備就緒。回到對話，直接描述需要瀏覽器完成的任務。',
    capabilitiesTitle: '智慧代理可以',
    sidebarStatus: '在側邊欄顯示連結狀態',
    reconnectHint: '保留授權，等待擴展自動重連。請確認瀏覽器和 BrowserSkill 擴展已開啟。',
    replaceDevice: '更換瀏覽器',
    installExtension: '安裝 BrowserSkill 擴展',
    storeInstall: 'Chrome 應用商店',
    edgeStoreInstall: 'Edge 載入項',
    extensionMinVersion: '需要 BrowserSkill v{version} 及以上版本，支持 Chrome 和 Edge。',
    extensionOutdated: '當前擴展版本 v{current} 過低，請升級到 v{version} 及以上。',
    manualInstall: '手動安裝（備用）',
    storeInstallHint: '在 Chrome 應用商店或 Edge 載入項中安裝 BrowserSkill，再回到這裡配對。',
    installHint: '無法存取商店或商店版本不相容時，可下載配套擴展並手動安裝。',
    downloadExtension: '下載配套擴展',
    officialExtension: '官方擴展（Chrome 應用商店）',
    installGuide: '如何安裝下載的擴展包？',
    pairGuide: '如何使用配對連結？',
    pairBrowser: '連結這台瀏覽器',
    packageUnavailable: '管理員尚未設定擴展下載包，請向管理員獲取配套版本。',
    manualCopy: '點擊下方輸入框複製連結，5 分鐘內有效，僅可配對一次。',
    pairingReady: '連結已複製。請在擴展中貼上，5 分鐘內有效，僅可配對一次。',
    copyAgain: '再次複製',
    usageTitle: '使用方式',
    usageStep1Title: '安裝擴展',
    usageStep1Text: '下載 ZIP 後解壓縮，在瀏覽器地址欄輸入 chrome://extensions（Edge 為 edge://extensions），開啟「開發者模式」，點擊「載入已解壓縮的擴展程式」，選擇解壓縮後的擴展目錄。',
    usageStep2Title: '配對這台瀏覽器',
    usageStep2Text: '複製配對連結，在擴展的「連結設定 → 遠程連結」中貼上並確認伺服器。配對一次，同一空間的各個對話共用。',
    usageStep3Title: '回到對話描述任務',
    usageStep3Text: '在對話輸入欄開啟「本機瀏覽器」，再傳送網頁任務。配對不會自動開啟此選項，任務會在獨立的任務視窗中運行。',
    usageStep4Title: '透過預覽查看和繼續',
    usageStep4Text: '對話裡會出現小預覽，點擊可定位到任務標籤。中斷或重連後任務仍會暫停，請在預覽中點繼續；借用已有分頁會先請你確認。',
    running: '運行中',
    locateWindow: '定位到瀏覽器',
    reconnectShort: '等待瀏覽器重連'
  },
  toolbox: {
    title: '工具箱',
    unavailable: '當前空間暫無可用的工具。'
  },
  automation: {
    conversationNotice: '此對話由自動化任務執行，無法手動傳送訊息。請在上方處理待審批事項。'
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
