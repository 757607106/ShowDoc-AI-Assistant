export default {
  memorySettings: {
    kinds: {
      profile: 'あなたについて',
      preference: '好み',
      fact: '事実',
      task: '進行中のタスク',
      interest: '長期的な関心'
    },
    usage: {
      title: 'メモリが使われるタイミング'
    }
  },
  imagePipeline: {
    smartocr: {
      name: 'スマート',
      description: 'まず画像の特徴を観察して説明を生成し、その特徴に基づいて OCR を実行するかどうかを判断します。モデル呼び出しを節約し、解析速度を向上させます 画像が補正可能な書類やラベルの写真と判定された場合、認識前にページを傾き補正・トリミングして OCR 精度を高めます。補正に失敗した場合は元の画像を使用します。',
      ocr: {
        thinking_enabled: {
          label: '文字認識時に思考を有効',
          description: 'テキストを抽出する前にモデルに考えさせます。基本的に思考は必要ありません。有効にすると解析が遅くなるだけでなく、思考が長くなりすぎて本文が切り詰められ、タスクが失敗する可能性があります。必要だと判断した場合のみ有効にしてください。'
        }
      },
      observation: {
        thinking_enabled: {
          label: '説明時に思考を有効',
          description: '画像を説明し属性を報告する前にモデルに考えさせます。基本的に思考は必要ありません。有効にすると解析が遅くなるだけでなく、思考が長くなりすぎて本文が切り詰められ、タスクが失敗する可能性があります。必要だと判断した場合のみ有効にしてください。'
        }
      },
      preprocess: {
        mode: {
          label: '文書の前処理',
          description: '初期設定はオフです。有効にすると OCR 前にページを補正・切り抜くため、処理時間が増えます。自動：観察結果で判断／常に：OCR 対象の画像を毎回前処理。処理中や制限超過の場合は元の画像を使用します。',
          options: {
            auto: '自動',
            off: 'オフ',
            always: '常に'
          }
        }
      },
      note_flow: {
        label: '観察結果が決めます',
        description: 'まず画像を説明し属性を観察し、返ってきた属性が OCR をもう一度行う価値があるかを決めます。ページを傾き補正すべきと属性が示した場合は、補正して周囲を切り落としてから読み取ります。その手順が利用できない場合は元の写真をそのまま読み取り、悪化することはありません。'
      },
      ocr_on_unobserved: {
        label: '画像属性の観察に失敗した場合も OCR を実行',
        description: 'モデルが画像属性を正しく観察できなかった場合、本文テキストを逃さないようデフォルトで OCR を実行します。オフにするとスキップします。（4B など小規模な視覚モデルを使う場合や、カスタムの画像指示がシステムプロンプトと衝突する場合に観察が失敗することがあります。8B 以上は失敗の可能性が低く、オフは推奨しません）'
      }
    },
    default: {
      name: 'マニュアル',
      description: 'タスクに合わせて解析アクションのスイッチを手動でオン/オフします。',
      ocr: {
        thinking_enabled: {
          label: '文字認識時に思考を有効',
          description: 'テキストを抽出する前にモデルに考えさせます。基本的に思考は必要ありません。有効にすると解析が遅くなるだけでなく、思考が長くなりすぎて本文が切り詰められ、タスクが失敗する可能性があります。必要だと判断した場合のみ有効にしてください。'
        }
      },
      caption: {
        thinking_enabled: {
          label: '説明時に思考を有効',
          description: '説明を書く前にモデルに考えさせます。基本的に思考は必要ありません。有効にすると解析が遅くなるだけでなく、思考が長くなりすぎて本文が切り詰められ、タスクが失敗する可能性があります。必要だと判断した場合のみ有効にしてください。'
        }
      },
      ocr_enabled: {
        label: '文字認識',
        description: '画像内に出現するテキストを抽出します。'
      },
      caption_enabled: {
        label: '画像説明',
        description: '各画像について一言の説明を生成し、キャプションとして保存します。'
      },
      note_actions: {
        label: '2 つの動作は独立しています',
        description: 'それぞれ個別に切り替えられます。識別をオフにしても画像は説明され、説明をオフにしても文字は抽出されます。両方をオフにしたときだけ画像は何も処理されないため、パネルはその組み合わせを許可しません。'
      }
    },
    errors: {
      noActionEnabled: '解析アクションを1つ以上オンにしてください。オフのままでは何も処理されません。'
    }
  },
  imageAttr: {
    layout_upright: {
      label: '文字の向き',
      description: '画像内の文字が正立しているか。傾いた・逆さまのページは OCR の前に傾き補正する価値があります。',
      values: {
        false: {
          label: '非正立',
          description: '回転・傾き撮影・逆さま'
        },
        true: {
          label: '正立',
          description: '文字が通常の向き'
        }
      }
    },
    layout_margin: {
      label: '版面の余白',
      description: '内容の外側（机・背景・余白）が画面全体に占める割合。余白が大きいほど、OCR の前にページをより詰めて切り出せます。',
      values: {
        large: {
          label: '余白大',
          description: '非文字領域が広い —— 机・部屋・ほぼ空白のページ'
        },
        small: {
          label: '余白少',
          description: '縁に細い帯だけ'
        },
        none: {
          label: '余白なし',
          description: '文字がほぼ画面いっぱい'
        }
      }
    },
    contain_data_visual: {
      label: 'データ可視化',
      description: '画像がグラフ・図表・ダイアグラム・インフォグラフィックとしてデータを伝えているか。文字が少なく見えても OCR の対象に残します。',
      values: {
        false: {
          label: 'いいえ',
          description: 'いいえ —— 写真・イラスト・アイコン・装飾'
        },
        true: {
          label: 'はい',
          description: 'はい —— グラフ・図表・ダイアグラム'
        }
      }
    },
    contain_text: {
      label: '画像内のテキスト量',
      description: '画像自体がどれだけ本文テキストを含むか。テキスト読み取りのために別途 OCR を行う価値があるかを判断します。',
      values: {
        block: {
          label: 'まとまった本文',
          description: 'まとまった本文 —— スクリーンショット、表、文書ページ'
        },
        sparse: {
          label: 'わずかな文字',
          description: 'わずかな文字のみ —— ロゴ、道路標識、単一のラベル'
        },
        none: {
          label: 'テキストなし',
          description: 'テキストは一切含まれていません'
        }
      }
    }
  },
  tenantInvitation: {
    errors: {
      notPending: 'この招待はすでに保留中ではありません。',
      forbidden: '招待された本人のみがこの招待を承諾・辞退できます。',
      notFound: '招待が見つからないか、すでに取り消されています。',
      generic: '問題が発生しました。もう一度お試しください。'
    },
    myInbox: {
      title: '自分への招待',
      description: '他のワークスペースからの招待です。承諾すると、割り当てられたロールで参加します。',
      empty: '保留中の招待はありません。',
      acceptButton: '承諾',
      declineButton: '辞退',
      acceptSuccess: '「{tenant}」に参加しました。',
      declineSuccess: '招待を辞退しました。',
      from: '招待者',
      tenantLabel: 'ワークスペース',
      expiresIn: '有効期限: {date}',
      messageLabel: 'メッセージ'
    }
  },
  tenantMember: {
    title: 'メンバー管理',
    loading: 'メンバーを読み込み中…',
    retry: '再試行',
    audit: {
      action: {
        'rbac.member_added': 'メンバー追加',
        'rbac.member_removed': 'メンバー削除',
        'rbac.member_role_changed': 'ロール変更',
        'rbac.member_left': 'メンバー退出',
        'rbac.access_denied': 'アクセス拒否',
        'rbac.invitation_sent': '招待送信',
        'rbac.invitation_accepted': '招待承諾',
        'rbac.invitation_declined': '招待辞退',
        'rbac.invitation_revoked': '招待取り消し',
        'rbac.invitation_expired': '招待期限切れ'
      }
    },
    errors: {
      lastOwner: '最後のオーナーの降格・削除・退出はできません。先に他のメンバーをオーナーに昇格させてください。',
      generic: '問題が発生しました。もう一度お試しください。'
    },
    leave: {
      confirmTitle: 'このワークスペースから退出しますか？',
      confirmBody: 'このワークスペース内のすべてのナレッジベースとエージェントにアクセスできなくなります。後で再度招待してもらうことは可能です。',
      confirm: '退出',
      success: 'ワークスペースから退出しました'
    },
    role: {
      owner: 'オーナー',
      admin: '管理者',
      contributor: '編集者',
      viewer: '閲覧者'
    },
    permissions: {
      title: 'ロール権限',
      desc: '各ロールがこのワークスペース内でできることを示します。サーバ側で強制され、UIの表示はそのルールを反映したものにすぎません。'
    }
  },
  userProfile: {
    title: 'ユーザ情報',
    description: 'アカウント情報（ユーザID、ユーザ名、アカウント、登録日時）を確認し、パスワードを変更できます。',
    changePassword: {
      label: 'パスワードを変更',
      description: '現在のパスワードを確認してから新しいパスワードを設定します。ログイン中のすべてのセッションは無効化され、再度ログインが必要になります。',
      currentLabel: '現在のパスワード',
      currentPlaceholder: '現在のパスワードを入力してください',
      currentRequired: '現在のパスワードを入力してください',
      newLabel: '新しいパスワード',
      newPlaceholder: '新しいパスワードを入力してください',
      confirmLabel: '新しいパスワード（確認）',
      confirmPlaceholder: '新しいパスワードをもう一度入力してください',
      submit: 'パスワードを更新',
      success: 'パスワードを更新しました。新しいパスワードでログインしてください。',
      failed: 'パスワードの変更に失敗しました。現在のパスワードが正しいか確認してください。',
      policyFailed: '新しいパスワードは8〜32文字で、英字と数字を含める必要があります',
      sameAsCurrent: '新しいパスワードは現在のパスワードと異なる必要があります',
      oidcOnlyDescription: 'このアカウントはOIDCログインで作成されたため、ローカルパスワードが設定されていません。'
    }
  },
  credential: {
    configured: '設定済み',
    unconfigured: '未設定',
    configure: '設定',
    update: '差し替え',
    remove: '削除',
    inputPlaceholder: '値を入力してください',
    savedToast: '認証情報を保存しました',
    saveFailed: '認証情報の保存に失敗しました',
    removedToast: '認証情報を削除しました',
    removeFailed: '認証情報の削除に失敗しました',
    confirmRemovePrompt: 'この認証情報を削除してもよろしいですか？この操作は取り消せません。',
    confirmRemove: '削除'
  },
  integrations: {
    claw: {
      title: 'WeKnora Skill'
    },
    chrome: {
      title: 'ナレッジアシスタント'
    },
    agentEditor: {
      desc: 'このエージェントをIMプラットフォームやWebサイトに公開します。管理は「公開と連携」から行います。'
    },
    embedOverview: {
      title: 'Web埋め込みチャネル'
    },
    imOverview: {
      title: '接続済みのIMチャネル'
    },
    api: {
      title: 'API連携',
      updateApiKeyScopeFailed: 'APIキーの更新に失敗しました'
    },
    tabs: {
      im: 'IM連携',
      embed: 'Web埋め込み',
      api: 'API連携',
      chrome: 'Chrome拡張機能',
      cli: 'CLI',
      claw: 'Clawスキル',
      mcpserver: 'MCP サーバー'
    },
    mcpserver: {
      title: 'MCP サーバー',
      tools: {
        list_knowledge_bases: 'ナレッジベース一覧',
        list_knowledge_basesDesc: '範囲内のナレッジベースと対応する検索方式を返します',
        search_knowledge: 'セマンティック検索',
        search_knowledgeDesc: '自然言語の質問に関連する箇所を出典付きで検索します',
        grep_chunks: 'キーワード / 正規表現検索',
        grep_chunksDesc: 'チャンク本文に対する大文字小文字を区別しない正規表現検索。固有名詞やコードに最適',
        list_documents: 'ドキュメント一覧',
        list_documentsDesc: 'ナレッジベース内のドキュメントをページ単位で一覧します',
        read_document: 'ドキュメントを読む',
        read_documentDesc: 'ドキュメントのメタ情報とチャンクを順に読みます',
        ask: '質問する',
        askDesc: 'エンドポイントに設定されたエージェントを実行し、引用付きの回答を返します。続きの質問にも対応',
        wiki_search: 'Wiki を検索',
        wiki_searchDesc: '生成された Wiki ページを検索します',
        wiki_read_page: 'Wiki ページを読む',
        wiki_read_pageDesc: 'slug を指定して Wiki ページを読みます',
        wiki_index: 'Wiki 目次',
        wiki_indexDesc: 'ナレッジベースの Wiki の目次を表示します',
        add_document: 'ドキュメント追加',
        add_documentDesc: 'Markdown テキストまたは URL からドキュメントを追加します',
        update_document: 'ドキュメント更新',
        update_documentDesc: 'Markdown ドキュメントの内容やタイトルを置き換えます',
        delete_document: 'ドキュメント削除',
        delete_documentDesc: 'ドキュメントとインデックスを完全に削除します'
      },
      groups: {
        retrieve: '検索と閲覧',
        chat: '質問応答',
        wiki: 'Wiki',
        ingest: '書き込み（慎重に有効化）'
      }
    },
    cli: {
      title: 'WeKnora CLI'
    }
  },
  datasource: {
    title: 'データソース',
    description: 'このナレッジベースにコンテンツを同期する外部データソースを設定します',
    add: 'データソースを追加',
    empty: 'データソースが設定されていません',
    edit: '編集',
    delete: '削除',
    deleteConfirm: 'このデータソースを削除しますか？同期済みのナレッジは削除されません。',
    deleteSuccess: 'データソースを削除しました',
    deleteFailed: '削除に失敗しました',
    syncNow: '今すぐ同期',
    syncTriggered: '同期タスクを送信しました',
    syncFailed: '同期の開始に失敗しました',
    pause: '一時停止',
    resume: '再開',
    paused: '一時停止しました',
    resumed: '再開しました',
    pauseFailed: '一時停止に失敗しました',
    logs: 'ログ',
    syncModeLabel: '同期モード',
    parseModeLabel: '解析モード',
    parseModeHint: 'Feishuクラウドドキュメントの解析方式。ブロック解析は高速でドキュメント内の添付ファイルを保持します。エクスポート解析はdocxに変換して解析し、画像とドキュメントの関連付けがより正確になります。',
    createTitle: 'データソースを追加',
    editTitle: 'データソースを編集',
    nameLabel: '名前',
    namePlaceholder: 'データソース名を入力してください',
    sectionBasic: '基本情報',
    testConnection: '接続テスト',
    testSuccess: '接続に成功しました',
    testFailed: '接続に失敗しました',
    connected: '接続済み',
    connectionFailed: '接続に失敗しました',
    isRequired: 'は必須です',
    credentialsLabel: '認証情報',
    resourceHint: '同期するスペースまたはフォルダを選択してください',
    untitled: '無題',
    resourceLoadFailed: 'リソースの読み込みに失敗しました',
    noResources: 'Wikiスペースが見つかりません',
    noResourcesDesc: 'コンテンツを取得するには、グループチャット経由でアプリにWikiのアクセス権限を付与する必要があります',
    noResourcesDesc_notion: 'コンテンツを取得するには、アプリにNotionページのアクセス権限が必要です',
    retryLoadResources: '再試行',
    guideStep1: 'Feishuでグループチャットを作成し、グループ設定でアプリをボットとして追加します',
    guideStep2: 'Wikiの「設定」>「メンバー設定」>「メンバーを追加」を開き、グループチャットを検索して追加します',
    guideStep3: 'グループチャットのロールが「閲覧可能」以上であることを確認し、戻って「再試行」をクリックします',
    guideStep1_notion: '同期したいページまたはデータベースをNotionで開きます',
    guideStep2_notion: '右上の「···」メニューをクリックし、「Connect to」または「Add connections」を選択します',
    guideStep3_notion: '作成したIntegrationアプリを検索して選択し、戻って「再試行」をクリックします',
    noResourcesDesc_nextcloud: 'アクセス可能なフォルダーや対応ファイルがありません',
    guideStep1_nextcloud: 'Nextcloud にログインし、対象フォルダーの読み取り権限を確認します',
    guideStep2_nextcloud: '「個人設定 → セキュリティ → デバイスとセッション」でアプリパスワードを作成します',
    guideStep3_nextcloud: 'ここで認証情報を置き換え、リソースを再読み込みします',
    noResourcesDesc_seafile: 'このトークンでアクセスできるライブラリがないか、すべて暗号化ライブラリです（暗号化ライブラリは同期できません）',
    guideStep1_seafile: 'Seafileにサインインし、アカウントが暗号化されていないライブラリを1つ以上読めることを確認します',
    guideStep2_seafile: '「設定 → Web APIトークン」でトークンを生成または再生成します',
    guideStep3_seafile: 'ここに戻って新しいトークンを入力し、「再試行」をクリックします',
    permissionDocLink: 'FeishuのWiki権限ドキュメントを見る',
    syncScheduleLabel: '同期スケジュール',
    conflictLabel: '競合時の処理',
    syncDeletions: '削除を同期（同期元で削除されたナレッジをナレッジベースからも削除）',
    createAndSync: '作成して今すぐ同期',
    createAndSyncSuccess: 'データソースを作成し、同期タスクを送信しました',
    createButSyncFailed: 'データソースを作成しましたが、同期の開始に失敗しました',
    updateSuccessSyncHint: 'データソースを更新しました。編集しただけでは同期は自動的に開始されません。変更を取り込むには「同期」をクリックしてください。',
    saveFailed: '保存に失敗しました',
    syncHistory: '同期履歴',
    refreshLogs: 'ログを更新',
    noLogs: '同期記録はまだありません',
    comingSoon: '近日対応予定',
    docHint: '認証情報の取得先:',
    openDoc: 'ドキュメントを開く',
    prereqBarText: '初めてですか？クリックしてFeishuアプリの設定ガイドを表示',
    prereqBarText_yuque: '初めてですか？クリックしてYuqueトークンの設定ガイドを表示',
    prereqStep1Brief_yuque: 'Yuqueのパーソナルトークンを作成',
    prereqStep1Desc_yuque: 'Yuqueにログイン → アバター → 設定 → トークン → 新しいトークン',
    prereqStep2Brief_yuque: 'トークンに必要な権限を付与',
    prereqStep2Desc_yuque: '少なくともrepo:readとdoc:read（ナレッジベースとドキュメント内容の読み取り）にチェックを入れます',
    prereqStep3Brief_yuque: '（任意）エンタープライズ導入の場合はベースURLを入力',
    prereqStep3Desc_yuque: 'パブリッククラウドの場合は空欄のままにします。Yuque Enterpriseやセルフホストの場合は、自社のドメインを入力してください。',
    prereqStep1Brief_feishu: 'Feishuのカスタムアプリを作成',
    prereqStep1Desc_feishu: 'Feishuオープンプラットフォームにログイン → 企業向けカスタムアプリを作成',
    prereqStep2Brief_feishu: 'ボット機能を追加',
    prereqStep2Desc_feishu: 'オープンプラットフォーム → 対象アプリ → アプリ機能を追加 → ボット',
    prereqStep3Brief_feishu: 'アプリの権限を設定',
    prereqStep3Desc_feishu: 'wiki:wiki:readonly、drive:drive:readonly、drive:export:readonly、docx:document:readonlyの権限を有効にします',
    prereqStep1Brief_lark: 'Larkのカスタムアプリを作成',
    prereqStep1Desc_lark: 'Larkオープンプラットフォームにログイン → 企業向けカスタムアプリを作成',
    prereqStep2Brief_lark: 'ボット機能を追加',
    prereqStep2Desc_lark: 'オープンプラットフォーム → 対象アプリ → アプリ機能を追加 → ボット',
    prereqStep3Brief_lark: 'アプリの権限を設定',
    prereqStep3Desc_lark: 'wiki:wiki:readonly、drive:drive:readonly、drive:export:readonly、docx:document:readonlyの権限を有効にします',
    prereqStep1Brief_feishu_drive: 'Feishuのカスタムアプリを作成',
    prereqStep1Desc_feishu_drive: 'Feishuオープンプラットフォームにログイン → 企業向けカスタムアプリを作成',
    prereqStep2Brief_feishu_drive: 'ボット機能を追加',
    prereqStep2Desc_feishu_drive: 'オープンプラットフォーム → 対象アプリ → アプリ機能を追加 → ボット',
    prereqStep3Brief_feishu_drive: 'アプリの権限を設定',
    prereqStep3Desc_feishu_drive: 'drive:drive:readonly、drive:export:readonly、docx:document:readonlyの権限を有効にします',
    prereqStep1Brief_lark_drive: 'Larkのカスタムアプリを作成',
    prereqStep1Desc_lark_drive: 'Larkオープンプラットフォームにログイン → 企業向けカスタムアプリを作成',
    prereqStep2Brief_lark_drive: 'ボット機能を追加',
    prereqStep2Desc_lark_drive: 'オープンプラットフォーム → 対象アプリ → アプリ機能を追加 → ボット',
    prereqStep3Brief_lark_drive: 'アプリの権限を設定',
    prereqStep3Desc_lark_drive: 'drive:drive:readonly、drive:export:readonly、docx:document:readonlyの権限を有効にします',
    prereqOpenConsole_yuque: 'Yuqueのトークン設定を開く',
    yuqueFolderModeLabel: 'フォルダ構成',
    yuqueFolderModeToc: 'Yuqueの目次どおりに階層化',
    yuqueFolderModeNone: 'ルートに平置き',
    yuqueFolderModeHint: 'Yuqueの目次階層に従って文書を配置します。なお、その後ナレッジベース上で手動で移動したフォルダは、次回その文書を同期したときにYuqueの構成へ上書きされます。',
    yuqueTOCOnly: 'Yuqueの目次に表示される文書だけ同期',
    yuqueTOCOnlyHint: '「Yuqueの目次どおりに階層化」を選ぶと有効になります。すでにナレッジベースにある文書はそのまま残り、Yuqueの目次にない文書は新たに追加されなくなるだけで、削除はされません。',
    dingtalkIngestLabel: 'DingTalk の取り込み範囲',
    dingtalkIncludeUploadedFiles: 'アップロードファイル（docx / pptx / xlsx / pdf）を取り込む',
    dingtalkIncludeUploadedFilesHint: '既定ではオフです。オンにすると、選択範囲にアップロードされた Word / PowerPoint / Excel / PDF ファイルをダウンロードして解析し、ナレッジベースに取り込みます（1 ファイルあたり 64 MiB まで）。本文はストレージと埋め込みのコストに算入されます。オフの場合は単にスキップされ、同期ログにスイッチが無効である旨が記録されます。既にナレッジベースにあるコピーは削除されません。',
    prereqBarText_dingtalk: '初めての利用ですか？DingTalkアプリの設定ガイドを確認',
    prereqStep1Brief_dingtalk: '企業内部アプリを作成',
    prereqStep1Desc_dingtalk: 'DingTalk開発者プラットフォームで企業内部アプリを作成し、Client IDとClient Secretを取得します。',
    prereqStep2Brief_dingtalk: 'ナレッジベースの読み取り権限を付与',
    prereqStep2Desc_dingtalk: 'Wiki.Workspace.Read、Wiki.Node.Read、Storage.File.Readを有効にします。',
    prereqStep3Brief_dingtalk: '操作ユーザーのUnion IDを入力',
    prereqStep3Desc_dingtalk: '対象ナレッジベースにアクセスできるDingTalkユーザーのUnion IDを入力します。',
    prereqOpenConsole_dingtalk: 'DingTalk開発者プラットフォームを開く',
    prereqBarText_ima: '初めてですか？クリックしてTencent IMA OpenAPIの設定ガイドを表示',
    prereqStep1Brief_ima: 'IMAエージェントのOpenAPI利用を申請',
    prereqStep1Desc_ima: 'https://ima.qq.com/agent-interfaceにサインインし、OpenAPIの利用を申請します',
    prereqStep2Brief_ima: 'ClientIDとAPIKeyを取得',
    prereqStep2Desc_ima: 'agent-interfaceのページからima-openapi-clientidとima-openapi-apikeyの認証情報をコピーします',
    prereqStep3Brief_ima: '対象のナレッジベースへのアクセス権を認証情報に付与',
    prereqStep3Desc_ima: 'IMAクライアントで、同期したいナレッジベースへのアクセスを認証情報に許可します。許可されていないナレッジベースは一覧に表示されません',
    prereqOpenConsole_ima: 'Tencent IMA OpenAPIコンソールを開く',
    prereqBotBrief: 'アプリに「ボット」機能を追加',
    prereqBotDesc: 'オープンプラットフォーム → アプリ機能を追加 → ボット → バージョンを作成して公開',
    prereqPermBrief: 'API権限を付与',
    prereqOpenConsole: 'Feishu開発者コンソールを開く',
    prereqMemberBrief: 'グループチャット経由でアプリをWikiに追加',
    prereqMemberDesc: 'グループチャットを作成 → アプリをボットとして追加 → グループチャットをWikiのメンバーに追加',
    back: '戻る',
    next: '次へ',
    save: '保存',
    schedule30min: '30分ごと',
    schedule1h: '1時間ごと',
    schedule6h: '6時間ごと',
    schedule12h: '12時間ごと',
    schedule24h: '毎日',
    neverSynced: '未同期',
    justNow: 'たった今',
    minutesAgo: '{n}分前',
    hoursAgo: '{n}時間前',
    daysAgo: '{n}日前',
    syncError: {
      dingtalk_document_failed: 'DingTalkドキュメントを読み取れません。アクセス権限を確認して同期を再試行してください。',
      dingtalk_document_too_large: 'DingTalkファイルが64 MiBのダウンロード上限を超えたため、今回の同期ではスキップしました。圧縮または分割してください。',
      dingtalk_resource_failed: 'DingTalkリソースを利用できません。アクセス権限と選択したリソースを確認して再試行してください。',
      deletion_lookup_failed: '削除前の項目の照会に失敗しました。サーバログを確認してください',
      deletion_failed: '削除に失敗しました。サーバログを確認してください',
      ingest_failed: '取り込みに失敗しました。サーバログを確認してください',
      nextcloud_permission_denied: 'Nextcloud ファイルへのアクセスが拒否されました。権限を確認してください。',
      nextcloud_not_found: '一覧取得後に Nextcloud ファイルが消失しました。次回再試行します。',
      nextcloud_file_too_large: 'Nextcloud ファイルが MAX_FILE_SIZE_MB を超えています。',
      nextcloud_empty_file: 'Nextcloud ファイルが空のためスキップしました。',
      nextcloud_source_changed: 'ダウンロード中に Nextcloud ファイルが変更されました。次回再試行します。',
      nextcloud_invalid_response: 'Nextcloud の WebDAV 応答が無効または不完全です。',
      nextcloud_ssrf_blocked: 'SSRF ポリシーが Nextcloud リクエストを拒否しました。SSRF_WHITELIST を確認してください。',
      nextcloud_fetch_failed: 'Nextcloud ファイルの取得に失敗しました。次回再試行します。',
      seafile_permission_denied: 'Seafileファイルへのアクセスが拒否されました。トークン所有者のライブラリ権限を確認してください。',
      seafile_not_found: 'Seafileファイルが存在しないか移動されました。次回の同期で再試行します。',
      seafile_file_too_large: 'Seafileファイルがサイズ上限を超えています。MAX_FILE_SIZE_MBを引き上げるかファイルを小さくしてください。',
      seafile_empty_file: 'Seafileファイルが空のためスキップしました。',
      seafile_source_changed: '取得中にSeafileファイルが変更されました。次回の同期で再試行します。',
      seafile_invalid_response: 'Seafileから解析できない応答が返されました。サーバのバージョンとリバースプロキシを確認してください。',
      seafile_ssrf_blocked: 'SeafileのダウンロードURLがSSRFポリシーでブロックされました。fileserverのホストをSSRF_WHITELISTに追加してください。',
      seafile_fetch_failed: 'Seafileからファイルを取得できませんでした。次回の同期で再試行します。'
    },
    resourceType: {
      wikiSpace: 'Wikiスペース',
      docCategory: 'ドキュメントタグ',
      book: 'Yuqueナレッジベース',
      library: 'Seafileライブラリ'
    },
    scheduleHuman: {
      '30min': '30分ごと',
      '1h': '1時間ごと',
      '6h': '6時間ごと',
      '12h': '12時間ごと',
      '24h': '毎日'
    },
    confluence: {
      cloudFolderLimitation: 'Confluence Cloud では、スペース直下のフォルダーなどコンテナ配下のページをここに一覧できません。スペース全体を選択すれば同期されます。'
    },
    field: {
      appId: 'App ID',
      appSecret: 'App Secret',
      clientId: 'Client ID',
      clientSecret: 'Client Secret',
      operatorId: '操作ユーザーのUnion ID',
      operatorIdHint: 'このユーザーの権限でナレッジベースを読み取ります。DingTalkのユーザー詳細APIで取得してください。',
      integrationToken: 'Integration Token',
      apiToken: 'APIトークン',
      confluenceEdition: 'Confluence エディション',
      confluenceEditionServer: 'Server / Data Center',
      confluenceEditionCloud: 'Cloud',
      confluenceBaseUrl: 'Confluence URL',
      confluenceUsername: 'ユーザー名またはメールアドレス',
      confluencePat: 'Server/DC 個人アクセストークン（PAT）',
      confluencePatHint: '任意。指定すると Bearer 認証を使用し、ユーザー名とパスワードは不要です。',
      confluencePassword: 'Server/DC パスワード',
      confluenceApiToken: 'Cloud API トークン',
      imaClientId: 'IMA ClientID',
      imaApiKey: 'IMA APIKey',
      baseUrl: 'ベースURL（任意）',
      baseUrlHint: '空欄の場合はデフォルトのパブリッククラウドのアドレスを使用します。プライベート/エンタープライズ導入の場合や、リバースプロキシ経由でアクセスする場合は、カスタムアドレスを入力してください（例: https://api-proxy.example.com）。',
      feedUrls: 'フィードURL',
      feedUrlsHint: '1行に1つのRSS / AtomフィードURLを入力します。複数のフィードを指定できます。',
      authHeaders: 'カスタムヘッダー（任意）',
      authHeadersHint: '非公開フィード用です。1行に1つ「名前: 値」の形式で入力します（例: Authorization: Bearer xxxx）'
    },
    drive: {
      folderTokenLabel: 'Driveフォルダトークン',
      folderTokenPlaceholder: 'folder_tokenまたはFeishu DriveのフォルダURLを入力してください',
      folderTokenRequired: '具体的なfolder_tokenを入力してください。クラウドスペースのルートは非対応です',
      rootNotSupportedHint: 'ルートフォルダはページングに対応せず、ショートカットも返されません。具体的なフォルダを選択してください',
      load: '読み込み',
      shareHint: '先にDriveフォルダをアプリのグループに共有してください。共有しないとアプリはアクセスできません',
      placeholderTitle: 'まずDriveフォルダを読み込んでください',
      placeholderDesc: '上部にfolder_token（またはFeishu DriveのフォルダURL）を入力し、「読み込み」をクリックしてください',
      loadForbiddenHint: 'アプリにこのフォルダへのアクセス権がありません。Feishu Driveでフォルダをアプリのグループに共有してから再試行してください。',
      loadAuthHint: 'アプリの認証情報が無効か、Driveのスコープが不足しています。App ID / App Secretとdrive:drive:readonly権限を確認してください。',
      loadNotFoundHint: 'folder_tokenが存在しないか、削除されています。Feishu DriveのフォルダURLからコピーしたトークンを確認してください。'
    },
    connectorDesc: {
      feishu: 'Feishu Wikiからドキュメント、スプレッドシート、ファイルを同期します',
      lark: 'Lark Wiki（Feishu国際版）からドキュメント、スプレッドシート、ファイルを同期します',
      feishu_drive: 'Feishu Driveのフォルダからドキュメント、スプレッドシート、ファイルを同期します',
      lark_drive: 'Lark Drive（Feishu国際版）のフォルダからドキュメント、スプレッドシート、ファイルを同期します',
      notion: 'Notionからページとデータベースを同期します',
      confluence: 'Confluence のスペースとページを Markdown として同期',
      yuque: 'Yuqueのナレッジベースからドキュメントを同期します',
      dingtalk: 'DingTalkナレッジベースのオンラインドキュメントを同期',
      rss: 'RSS / Atomフィードから記事を同期します',
      ima: 'Tencent IMAのナレッジベースからドキュメント、ノート、ファイルを同期します（AIセッションと動画の解析は非対応）',
      gitlab: 'GitLabプロジェクトからファイルを同期します',
      nextcloud: 'WebDAV 経由で Nextcloud のフォルダーとファイルを同期',
      seafile: 'Seafileライブラリのフォルダとファイルを同期します'
    },
    connector: {
      feishu: 'Feishu',
      lark: 'Lark',
      feishu_drive: 'Feishu Drive',
      lark_drive: 'Lark Drive',
      notion: 'Notion',
      confluence: 'Confluence',
      yuque: 'Yuque',
      dingtalk: 'DingTalkドキュメント',
      rss: 'RSS / Atomフィード',
      ima: 'Tencent IMA',
      gitlab: 'GitLab',
      nextcloud: 'Nextcloud',
      seafile: 'Seafile'
    },
    logDetail: {
      startTime: '開始',
      endTime: '終了',
      failedItems: '失敗したドキュメント',
      failedItemsMore: '他{n}件の失敗したドキュメントは表示されていません',
      docsFailedSummary: '{n}件のドキュメントの同期に失敗しました'
    },
    logSummary: {
      total: '実行回数',
      success: '成功',
      failed: '失敗',
      items: '件数'
    },
    logMetric: {
      total: '合計',
      skipped: 'スキップ',
      failed: '失敗'
    },
    logStatus: {
      running: '同期中',
      success: '成功',
      partial: '一部成功',
      failed: '失敗',
      canceled: 'キャンセル済み'
    },
    step: {
      selectType: 'タイプを選択',
      credentials: '認証情報',
      resources: 'リソース',
      strategy: '同期戦略'
    },
    conflict: {
      overwrite: '上書き',
      skip: '既存をスキップ'
    },
    seafile: {
      baseUrl: 'Seafile URL',
      apiToken: 'APIトークン',
      apiTokenHint: 'Seafileの「設定 → Web APIトークン」で生成します。アカウントに選択したライブラリの読み取り権限があれば十分で、トークンはファイルのダウンロード要求には送信されません。',
      singleLibraryOnly: '1つのデータソースは1つのライブラリのみ同期できます。別のライブラリを選ぶ前に現在の選択を解除してください。',
      selectionRequired: 'ライブラリ、フォルダまたはファイルを1つ以上選択してください'
    },
    nextcloud: {
      baseUrl: 'Nextcloud URL',
      baseUrlHint: 'https://nextcloud.example.com/cloud のようなインストール先を指定します。/remote.php/dav は含めません。プライベート環境では既存の SSRF_WHITELIST を設定してください。',
      username: 'ユーザー名',
      appPassword: 'アプリパスワード',
      appPasswordHint: '「個人設定 → セキュリティ → デバイスとセッション」で作成したユーザー名とアプリパスワードを使用します。',
      selectionRequired: 'フォルダーまたはファイルを1つ以上選択してください',
      includeExtensions: '含める拡張子（任意）',
      excludeExtensions: '除外する拡張子（任意）',
      extensionsHint: '.pdf, .md のようにカンマで区切ります。含める拡張子が空なら対応する全形式が対象です。除外が優先され、変更は削除の照合範囲にも影響します。'
    },
    gitlab: {
      baseUrl: 'GitLab URL',
      accessToken: 'パーソナルアクセストークン',
      projects: 'GitLabプロジェクト',
      projectsHint: 'プロジェクトIDまたはネームスペースのパス（例: group/project）を入力します。ブランチとディレクトリは任意です。',
      project: 'プロジェクト',
      projectId: 'プロジェクトID',
      projectIdPlaceholder: '例: 12345またはgroup/project',
      ref: 'ブランチ',
      refPlaceholder: '空欄の場合はデフォルトブランチを使用します',
      paths: 'ディレクトリ',
      pathsPlaceholder: '1行に1つのディレクトリを入力します。空欄の場合はプロジェクト全体を同期します',
      addProject: 'プロジェクトを追加',
      projectRequired: 'GitLabプロジェクトを1つ以上追加してください'
    },
    status: {
      active: '接続済み',
      paused: '一時停止中',
      error: 'エラー'
    },
    syncMode: {
      incremental: '増分',
      full: '全量'
    },
    parseMode: {
      inherit: 'サーバー設定を使用',
      blocks: 'ブロック解析（デフォルト）',
      export: 'エクスポート解析（docx）'
    }
  },
  mermaid: {
    diagram: '図',
    expand: '全画面表示',
    zoomIn: '拡大',
    zoomOut: '縮小',
    reset: 'リセット',
    download: '画像をダウンロード',
    close: '閉じる',
    downloading: 'ダウンロード中...'
  },
  agentEditor: {
    builtinHint: 'これは組み込みエージェントです。名前と説明は変更できませんが、設定パラメータは調整できます。',
    fileTypes: {
      label: '対応ファイル形式',
      desc: '選択できるファイル形式を制限します。空欄の場合はすべての形式に対応します',
      allTypes: 'すべての形式',
      pdf: 'PDFドキュメント',
      word: 'Wordドキュメント（.docx/.doc）',
      textLabel: 'テキスト',
      text: 'プレーンテキストファイル（.txt）',
      markdown: 'Markdownドキュメント',
      csv: 'カンマ区切りファイル',
      excel: 'Excelスプレッドシート（.xlsx/.xls）',
      imageLabel: '画像',
      image: '画像ファイル（.jpg/.jpeg/.png）'
    },
    fallback: {
      fixed: '固定応答',
      model: 'モデル生成'
    },
    faq: {
      title: 'FAQ優先戦略'
    },
    chatParser: {
      label: 'チャット添付ファイルの解析ポリシー',
      desc: 'このエージェントのチャット添付ファイルについて、ファイル種別ごとに解析エンジンを選択します。',
      waitTimeoutLabel: '添付ファイル解析の待機タイムアウト（秒）',
      waitTimeoutDesc: '1回の会話ターンで、解析中の添付ファイルを待つ最長時間です。この時間を超えると、解析が完了したファイルだけで回答を続行します。大きなファイルやスキャン文書では長めに設定してください。0でグローバルのデフォルトを使用します。'
    },
    audioUpload: {
      label: '音声アップロード',
      desc: '有効にすると、ユーザが会話中に音声ファイルをアップロードできます。システムは音声認識（ASR）モデルを使って自動的に文字起こしします。',
      asrModel: 'ASRモデル',
      asrModelDesc: '音声の文字起こしに使用する音声認識モデル。未設定の場合、音声ファイルはプレースホルダとして渡されます。',
      asrModelPlaceholder: 'ASRモデルを選択'
    },
    imageUpload: {
      navLabel: '添付ファイルのアップロード',
      sectionTitle: '添付ファイルのアップロード',
      sectionDesc: 'チャットでの画像・ドキュメント・音声の添付、および解析ルールと関連モデルを設定します',
      label: '画像アップロード',
      desc: 'チャットでユーザが画像をアップロードし、VLMで理解できるようにします',
      vlmModel: 'VLMモデル',
      vlmModelDesc: '画像解析に使用する視覚言語モデル',
      vlmModelPlaceholder: 'VLMモデルを選択',
      vlmModelRequired: '画像アップロードを有効にする場合、VLMモデルは必須です',
      imageUnderstandingLabel: '添付画像の理解 / スキャン文書のOCR',
      imageUnderstandingDesc: '画像のみのPDF/PPT（スキャンしたドキュメント）で、テキストを抽出できない場合にVLM OCRを実行します。解析に時間がかかるようになります。デフォルトは無効です。',
      ocrMaxPagesLabel: 'スキャンOCRの最大ページ数',
      ocrMaxPagesDesc: 'OCRのためVLMに送信するスキャンしたドキュメントの最大ページ数。ページ数を増やすとカバー範囲は広がりますが、解析は遅くコストも高くなります。0でグローバルのデフォルトを使用します。',
      useGlobalDefault: '0 = グローバルのデフォルト',
      storageProvider: '画像ストレージ',
      storageProviderDesc: 'アップロードした画像のストレージエンジン。空欄の場合はシステムのデフォルトを使用します',
      storageProviderPlaceholder: 'ストレージエンジンを選択',
      storageDefault: 'システムデフォルト',
      notConfigured: '未設定',
      goStorageSettings: 'ストレージ設定へ移動'
    },
    llmCallTimeout: {
      label: 'LLM呼び出しタイムアウト',
      desc: 'モデルクライアントのリクエストタイムアウト設定（秒）。出力が続くストリーミング応答では、全体の所要時間がこの値を超える場合があります。',
      hint: '空欄または0でデフォルト（120秒）を使用します',
      placeholder: '秒数を入力してください。推奨範囲は60〜1800'
    },
    mcp: {
      label: 'MCPサービス',
      desc: 'エージェントが使用できるMCPサービスを選択します',
      selectLabel: 'MCPサービスを選択',
      selectDesc: '有効にするMCPサービスを選択します',
      selectPlaceholder: 'MCPサービスを選択',
      authWaitTimeout: '認証待機タイムアウト（秒）',
      authWaitTimeoutDesc: '会話中にOAuth認証を求められた際、完了を待機する最大秒数です。この時間を過ぎると、認証の確認は自動的にスキップされます（OAuthを使用するMCPサービスのみに影響します）。',
      authWaitTimeoutPlaceholder: 'デフォルト600秒',
      accessLevel: '実行権限の上限',
      accessLevelDesc: 'データを変更するツール（MCP ツール、Wiki への書き込み）を確認なしで実行できるかどうか。読み取り専用ではこれらのツールを提供せず、変更前に確認では毎回確認します。承認が必要と設定された MCP ツールは常に確認します。',
      unavailableService: '利用できないサービス'
    },
    agentType: {
      label: 'エージェントタイプ',
      desc: 'プリセットを選択すると、システムプロンプト、ツール一覧、推奨されるナレッジベース範囲が自動入力されます。',
      defaultNamePattern: 'マイ{label}',
      kbIncompatibleWarn: '選択した{count}件のナレッジベースはこのタイプと互換性がありません。手動で調整してください。',
      kbMismatch: {
        ragQa: 'RAG検索が有効になっていません',
        wikiQa: 'Wikiが有効になっていません',
        hybridRagWiki: '利用できる検索手段がありません',
        dataAnalysis: 'RAGが必要です（FAQは非対応）',
        quickAnswer: 'クイック回答モードにはRAG検索が必要です',
        generic: '現在のタイプと互換性がありません'
      }
    },
    im: {
      title: 'IM連携',
      description: 'WeCom、Feishu、Lark、Slack、Telegram、DingTalk、Mattermost、WeChat、QQBot、Yunzhijiaなどのインスタントメッセージングプラットフォームにエージェントを接続します',
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
      addChannel: 'チャネルを追加',
      channelsTitle: 'IMチャネル',
      disabled: '無効',
      editChannel: 'チャネルを編集',
      deleteConfirm: 'このチャネルを削除してもよろしいですか？この操作は取り消せません。',
      channelName: 'チャネル名',
      channelNamePlaceholder: '識別しやすい名前を入力してください',
      channelNameDefaultHint: 'デフォルトはプラットフォーム名です。任意の名前に変更できます。空欄のまま保存するとプラットフォーム名が使用されます',
      platform: 'プラットフォーム',
      mode: '接続モード',
      outputMode: '出力モード',
      outputStream: 'ストリーミング',
      outputFull: '一括出力',
      callbackUrl: 'コールバックURL',
      empty: 'IMチャネルはまだありません',
      unnamed: '名称未設定のチャネル',
      docLink: '連携ガイド',
      wecomConsole: 'WeCom管理コンソール',
      feishuConsole: 'Feishuオープンプラットフォーム',
      larkConsole: 'Larkオープンプラットフォーム',
      slackConsole: 'Slack APIコンソール',
      telegramConsole: 'Telegram BotFather',
      dingtalkConsole: 'DingTalkオープンプラットフォーム',
      dingtalkCardTemplateId: 'カードテンプレートID（任意）',
      dingtalkCardTemplateIdHint: 'open-dev.dingtalk.com/fe/cardでAIカードテンプレートを作成すると、タイプライター効果のあるストリーミング出力を利用できます',
      mattermostConsole: 'Mattermost連携設定',
      qqbotConsole: 'QQオープンプラットフォーム',
      qqbotAPIBaseURLHint: '任意。空欄の場合はデフォルトの本番APIエンドポイントを使用します。',
      qqbotGatewayURLHint: '任意。空欄の場合は共通のWebSocketゲートウェイを自動取得します。',
      yunzhijiaConsole: 'Yunzhijiaオープンプラットフォーム',
      yunzhijiaRobotDoc: 'ボットメッセージのドキュメント',
      yunzhijiaImageDoc: '開発者プラットフォーム（画像）',
      yunzhijiaModeHint: 'WebhookとWebSocketに対応しています。WebSocketモードでは公開のコールバックURLは不要です。',
      yunzhijiaSendMsgUrl: 'メッセージ送信URL',
      yunzhijiaSendMsgUrlHint: 'ボットの返信に使用されます。',
      yunzhijiaSecret: '署名シークレット（任意）',
      yunzhijiaSecretPlaceholder: 'Yunzhijiaのボット設定にあるHmacSHA1署名シークレット',
      yunzhijiaSecretHint: '設定すると、受信するコールバックをHmacSHA1署名で検証します',
      yunzhijiaAppId: 'App ID（画像ダウンロード用）',
      yunzhijiaAppIdPlaceholder: 'YunzhijiaオープンプラットフォームのApp ID',
      yunzhijiaAppSecret: 'App Secret（画像ダウンロード用）',
      yunzhijiaAppSecretPlaceholder: 'YunzhijiaオープンプラットフォームのApp Secret',
      yunzhijiaAppCredentialHint: 'appAccessTokenの取得と、ユーザが送信した画像のダウンロードに使用されます。',
      yunzhijiaTimeout: 'HTTPタイムアウト（秒）',
      yunzhijiaTimeoutHint: 'メッセージ送信URL経由で返信を送る際のタイムアウト。デフォルトは10秒',
      yunzhijiaAllowedHostSuffix: '許可するホストのサフィックス',
      yunzhijiaAllowedHostSuffixHint: 'セキュリティのため、メッセージ送信URLのホストをこのサフィックスに制限します（例: yunzhijia.com）',
      yunzhijiaSendMsgUrlRequired: 'Yunzhijiaのボット設定にあるメッセージ送信URLを入力してください',
      mattermostModeHint: 'MattermostはWebhookモードのみ対応しています（送信Webhook + Botトークン）。',
      mattermostPostToMain: 'チャネルのタイムラインに返信を投稿',
      mattermostPostToMainHint: '有効にすると、Botの返信はチャネル内の新しいトップレベル投稿になります。無効（デフォルト）の場合はスレッド内に留まり、メインビューには「N件の返信」とだけ表示されます。',
      modeHint: '設定が簡単なWebSocketを推奨します',
      consoleTip: 'で認証情報を取得',
      wecomWSEndpointHint: '任意。WeComをセルフホストで導入している場合は、カスタムWebSocketアドレスを入力してください。空欄の場合はデフォルトのパブリッククラウドのエンドポイントを使用します。内部ネットワークのアドレスの場合は、ホスト名をSSRF_WHITELIST環境変数に追加してください。',
      wecomAPIBaseURLHint: '任意。WeComをセルフホストで導入している場合は、カスタムAPIベースURLを入力してください。空欄の場合はデフォルトのパブリッククラウドのエンドポイントを使用します。内部ネットワークのアドレスの場合は、ホスト名をSSRF_WHITELIST環境変数に追加してください。',
      feishuAPIBaseURLHint: '任意。サーバが直接インターネットに接続できる場合は空欄のままにしてください。Feishuへのアクセスにプロキシが必要な場合は、リバースプロキシのURL（例: nginx、http://host:port）を入力してください。内部ネットワークのアドレスの場合は、ホスト名をSSRF_WHITELIST環境変数に追加してください。',
      fileKnowledgeBase: 'ファイル保存先ナレッジベース',
      fileKnowledgeBasePlaceholder: 'ナレッジベースを選択（任意）',
      fileKnowledgeBaseHint: '設定すると、ユーザが送信したファイルがこのナレッジベースに自動的に保存されます',
      sessionMode: 'セッションモード',
      sessionModeUser: 'ユーザ単位（デフォルト）',
      sessionModeThread: 'スレッド単位',
      sessionModeHint: 'ユーザモード: 各ユーザが個別の会話を持ちます。/clearで新しく開始できます。スレッドモード: メッセージスレッドごとに個別の会話になります。同じスレッドで複数人が共同作業できます。',
      replyLanguage: '返信言語',
      replyLanguageDefault: 'システムのデフォルトを使用',
      replyLanguageHint: 'このチャネルでエージェントが返信する言語を固定します。未設定の場合はデプロイのデフォルト言語を使用します。',
      wechatScanBind: 'スキャンしてWeChatを連携',
      wechatScanning: 'WeChatでQRコードをスキャンしてください',
      wechatBindSuccess: 'WeChatを連携しました',
      wechatRebind: '再連携',
      wechatHint: 'iOS版WeChat 8.0.70以降が必要です。ダイレクトメッセージのみ対応しています',
      wechatQRExpired: 'QRコードの有効期限が切れました。再試行してください',
      wechatBinding: '連携中...',
      sectionChannel: 'チャネル情報',
      sectionConnection: '接続',
      sectionCredentials: 'プラットフォームの認証情報',
      selectPlatform: 'プラットフォームを選択',
      selectPlatformDesc: '接続するメッセージングプラットフォームを選択します',
      enabled: 'チャネルを有効化',
      stepBasic: '基本情報',
      stepConnection: '接続',
      stepKnowledge: 'ファイル保存',
      stepCredentials: '認証情報',
      sectionAccess: 'アクセスと出力',
      sectionSession: 'セッション',
      sectionCallback: 'コールバックURL',
      sectionKnowledge: 'ファイル保存',
      sectionStatus: 'ステータス'
    },
    embed: {
      title: 'Webページ埋め込み'
    },
    tools: {
      thinking: '思考',
      thinkingDesc: '動的かつ内省的に問題を解決する思考ツール',
      todoWrite: '計画',
      todoWriteDesc: '構造化された調査計画を作成します',
      askUser: 'ユーザーに質問',
      askUserDesc: '必要な情報が不足しているときにユーザーへ質問し、回答を待ってから続行します',
      searchKnowledge: 'ナレッジベースを検索',
      searchKnowledgeDesc: 'セマンティック・キーワード・ハイブリッド検索でナレッジベースのチャンクを検索します',
      readDocument: 'ドキュメントを読む',
      readDocumentDesc: 'ドキュメントのメタデータとチャンク内容を読み取ります。ページングと文書内検索に対応',
      listDocuments: 'ドキュメント一覧',
      listDocumentsDesc: 'ナレッジベース内のドキュメントをページ単位で一覧表示します',
      queryGraph: 'ナレッジグラフを照会',
      queryGraphDesc: 'ナレッジグラフからリレーションを照会します',
      dbQuery: 'データベースを照会',
      dbQueryDesc: 'データベースから情報を照会します',
      dataAnalysis: 'データ分析',
      dataAnalysisDesc: 'データファイルを理解し、データ分析を実行します',
      dataSchema: 'データスキーマを表示',
      dataSchemaDesc: '表形式ファイルのメタデータを取得します',
      requiresKb: '（ナレッジベースの設定が必要）',
      requiresRagKb: '（ベクトル/キーワードインデックスが有効なナレッジベースが必要）',
      requiresWikiKb: '（Wikiが有効なナレッジベースが必要）',
      wikiSearch: 'Wikiを検索',
      wikiSearchDesc: 'Wikiページをキーワード/セマンティック検索します',
      wikiReadPage: 'Wikiページを読み取り',
      wikiReadPageDesc: '特定のWikiページの全文を読み取ります',
      wikiFlagIssue: 'Wikiの問題を報告',
      wikiFlagIssueDesc: 'Wikiページの事実誤認やマージ競合を報告します',
      wikiWritePage: 'Wikiを作成/上書き',
      wikiWritePageDesc: '新しいページを作成、または既存のページを全面的に上書きします',
      wikiReplaceText: 'Wikiのテキストを置換',
      wikiReplaceTextDesc: 'Wikiページ内の特定のテキストを置換します',
      wikiRenamePage: 'Wikiページ名を変更',
      wikiRenamePageDesc: 'Wikiページの名前を変更し、相互リンクを自動更新します',
      wikiDeletePage: 'Wikiページを削除',
      wikiDeletePageDesc: 'Wikiページを削除し、リンク切れを整理します',
      wikiReadIssue: 'Wikiの問題を表示',
      wikiReadIssueDesc: 'Wikiページの問題の詳細を表示します',
      wikiUpdateIssue: 'Wikiの問題を更新',
      wikiUpdateIssueDesc: 'Wikiページの問題のステータスを更新します',
      webSearch: 'Web検索',
      webFetch: 'Webページ取得',
      groupBase: '基本',
      groupRag: 'ナレッジベース検索（RAG）',
      groupWikiRead: 'Wiki読み取り',
      groupWikiEdit: 'Wiki編集',
      groupWikiIssue: 'Wikiレビュー',
      groupData: 'データ分析',
      writeWarning: 'Wikiの内容を変更します',
      dangerTag: '書き込み',
      statusNoKb: 'ナレッジベースが紐付けられていません',
      kbMetricRag: 'RAGナレッジベース',
      kbMetricWiki: 'Wikiナレッジベース',
      statusInactive: '選択済みの{count}個のツールは、現在の設定では有効になりません',
      searchConversations: '過去の会話を検索',
      searchConversationsDesc: 'ユーザー自身の過去の会話から以前話した内容を探します',
      groupStored: '保存済み（ここでは提供されていません）',
      switchManagedDesc: 'このリストではなくエージェントの他の設定で制御されるため、ここでチェックしても有効になりません。チェックを外すと削除されます。',
      unrecognizedDesc: 'このバージョンにはないツールのため、エージェントは呼び出せません。チェックを外すと削除されます。',
      keptUnknownWarning: '保存しました。次の保存済みツールはこのバージョンにはないため残しましたが、エージェントは呼び出せません：{names}',
      droppedWarning: '保存しました。次のツールはエージェントの他の設定で制御されるため、ツールリストから削除しました：{names}',
      effectiveLabel: '有効なツール',
      effectiveDesc: '現在の設定から算出された、エージェントが実際に呼び出せるツールです',
      effectiveEmpty: '利用可能なツールがありません。エージェントは通常のモデル対話にフォールバックします'
    },
    desc: {
      name: 'エージェントを識別しやすい名前を設定します',
      description: 'エージェントの目的と特徴を簡潔に説明します',
      systemPrompt: 'エージェントの動作と役割を定義するカスタムシステムプロンプト',
      promptInheritance: 'テンプレートの原文は更新に追従し、編集した内容はカスタムプロンプトとして保存されます。エージェントモードでは役割と作業要件を定義します。ツール権限と各ターンの情報源選択は別途制御されます。',
      useCustomSystemPrompt: 'デフォルトペルソナを置き換える',
      useCustomSystemPromptDesc: 'オンにするとこのプロンプトがプラットフォームのデフォルトペルソナを置き換えます。ツール使用と引用の規約は引き続きプラットフォームが注入します。オフの場合は追加指示としてデフォルトペルソナの後に付与されます。',
      leaveEmptyDefault: '（空欄の場合はシステムのデフォルトを使用）',
      contextTemplate: '検索した内容をモデルに渡す前の整形方法を定義します',
      model: 'エージェントが使用するLLMを選択します',
      temperature: '出力のランダム性を制御します。0が最も決定的、1が最もランダムです',
      maxTokens: 'モデルの応答の最大トークン数。デフォルトは2048です。カスタム値は入力したとおりに保存されます。',
      maxTokensAgent: '推論の各ラウンドで生成される最大トークン数（ツール呼び出しのJSONを含む）。デフォルトは24576です。カスタム値は入力したとおりに保存されます。',
      thinking: '拡張思考機能を有効にします（モデルの対応が必要）',
      queryUnderstandModel: 'クエリ理解（リライトとインテント判定）に使用するモデル。空欄の場合はメインのチャットモデルを使用します。',
      rewriteSystemPrompt: '質問リライト用のシステムプロンプト（空欄でデフォルト）',
      rewriteUserPrompt: '質問リライト用のユーザプロンプトテンプレート（空欄でデフォルト）',
      selectTools: 'エージェントが使用できるツールを選択します',
      maxIterations: 'メインエージェントが1ターンにモデルを呼び出せる回数を制限します。',
      kbScope: 'エージェントがアクセスできるナレッジベースの範囲を選択します',
      fallbackStrategy: 'ナレッジベースで関連する内容が見つからない場合の処理方法',
      fallbackResponse: '回答できない場合に返す固定テキスト',
      fallbackPrompt: 'ナレッジベースで回答が見つからない場合に、モデルの応答を導くプロンプト',
      memoryEnabled: 'このエージェントが長期メモリを読み取り、追記できるようにします。無効にすると、このエージェントとの会話はメモリを読み取らず、新しいメモリも追加しません。ワークスペースまたは個人の設定が無効の場合、ここで有効にしても反映されません'
    },
    selection: {
      all: 'すべて',
      selected: '選択済み',
      disabled: '無効'
    },
    promptNav: {
      ariaLabel: 'プロンプトのアウトライン',
      system: 'システムプロンプト',
      context: 'コンテキストテンプレート',
      intent: 'インテントプロンプト',
      rewriteSystem: 'リライト · システム',
      rewriteUser: 'リライト · ユーザ',
      fallback: '検索フォールバック'
    },
    intentPrompts: {
      title: 'インテントプロンプト',
      sectionDesc: 'インテントごとのシステムプロンプトを設定します。未設定の場合はデフォルトが適用されます',
      intentLabel: 'インテント',
      promptPlaceholder: 'カスタムシステムプロンプトを入力してください...',
      customized: 'カスタム済み',
      empty: '利用可能なインテントテンプレートがありません'
    },
    placeholders: {
      available: '使用可能な変数: ',
      clickToInsert: '（クリックで挿入）',
      hint: '（クリックで挿入、または{\'{{\'}を入力して一覧を表示）'
    },
    questionSuggestions: {
      title: '会話の質問サジェスト'
    },
    navGroups: {
      basic: '基本',
      knowledge: 'ナレッジと検索',
      capability: '拡張機能'
    }
  },
  agentStream: {
    saveToKb: {
      emptyContent: '現在の応答は空のため、ナレッジベースに保存できません',
      editorOpened: 'エディタを開きました。ナレッジベースを選択して保存してください'
    },
    copy: {
      emptyContent: '現在の応答は空のため、コピーできません',
      success: 'クリップボードにコピーしました',
      failed: 'コピーに失敗しました。手動でコピーしてください'
    },
    toolStatus: {
      calling: '{name}を呼び出し中...',
      searchKb: 'ナレッジベースを検索',
      searchKbFailed: 'ナレッジベースの検索に失敗しました',
      searchMixed: 'ナレッジベースとWebを検索しました',
      searchMixedFailed: '検索に失敗しました',
      webSearch: 'Web検索',
      webSearchFailed: 'Web検索に失敗しました',
      grepSearch: 'キーワード検索',
      grepSearchFailed: 'キーワード検索に失敗しました',
      getDocInfo: 'ドキュメント情報を取得中',
      getDocInfoFailed: 'ドキュメント情報の取得に失敗しました',
      viewDocument: 'ドキュメントを表示',
      thinkingDone: '思考完了',
      thinkingFailed: '思考に失敗しました',
      updateTodos: 'タスクリストを更新中',
      updateTodosFailed: 'タスクリストの更新に失敗しました',
      imageAnalyzing: '画像の内容を確認中...',
      imageAnalysisDone: '画像の内容を確認しました',
      imageAnalysisFailed: '画像の確認に失敗しました',
      attachmentParsing: '添付ファイルを解析中...',
      attachmentParsingDone: '添付ファイルを解析しました',
      attachmentParsingFailed: '添付ファイルの解析に失敗しました',
      queryUnderstanding: 'クエリを理解中...',
      queryUnderstandDone: 'クエリを理解しました',
      called: '{name}を呼び出しました',
      calledFailed: '{name}の呼び出しに失敗しました',
      shellExecRunning: 'サンドボックスコマンドを実行中...'
    },
    mcp: {
      discoverTools: 'MCP ツールを検出',
      listServers: 'MCP サービス一覧',
      listTools: 'MCP ツール一覧',
      searchTools: 'MCP ツールを検索',
      describeTool: 'ツール定義を確認',
      callTool: 'MCP ツールを実行',
      showing: '{total} 件中 {count} 件を表示',
      moreAvailable: '他にも結果があります',
      empty: '表示する項目はありません',
      parameters: 'パラメーター',
      expand: '説明を表示',
      collapse: '閉じる',
      required: '必須',
      fullSchema: '完全なパラメータ定義',
      failed: 'MCP 操作に失敗しました',
      result: '実行結果'
    },
    ragPipeline: {
      searching: 'ナレッジベースを検索中...',
      searchingWithQuery: 'ナレッジベースを検索中:「{query}」',
      searchingWeb: 'Webを検索中...',
      searchingWebWithQuery: 'Webを検索中:「{query}」',
      searchingMixed: 'ナレッジベースとWebを検索中...',
      searchingMixedWithQuery: 'ナレッジベースとWebを検索中:「{query}」',
      searchDone: '検索完了'
    },
    attachmentParsing: {
      parsedSummary: '{count}件の添付ファイルを解析しました',
      parsedWithSkipped: '{parsed}件の添付ファイルを解析し、{skipped}件はスキップしました（処理中）',
      noneReady: '解析済みの添付ファイルがありません'
    },
    knowledgeChunksList: {
      chunkRange: '{fetched} / {total}チャンクを読み込みました',
      page: '{page}ページ目、1ページあたり{pageSize}件',
      offsetRange: 'チャンク {from}–{to}',
      queryMatches: '文書内検索「{query}」: {count}件一致',
      queryNoMatch: '文書内検索「{query}」: 一致なし'
    },
    grepResults: {
      chunkHits: '{count}チャンク',
      keywordHits: '{count}件ヒット',
      titleMatch: 'タイトル一致',
      faqEntry: 'FAQ項目'
    },
    search: {
      noResults: '一致するコンテンツが見つかりません',
      candidatesBelowThreshold: '{count}件の候補が一致しましたが、関連性が不十分なため回答には使用しませんでした',
      foundResultsFromFiles: '{files}件のファイルから{count}件の結果が見つかりました',
      foundResults: '{count}件の結果が見つかりました',
      foundMixedResults: '{count}件の結果が見つかりました（ドキュメント{docCount}件、Web検索結果{webCount}件）',
      webResults: '{count}件のWeb検索結果が見つかりました',
      grepSummary: '{docs}件のドキュメントで{chunks}件の一致するチャンクが見つかりました'
    },
    plan: {
      inProgress: '進行中',
      pending: '未着手',
      completed: '完了'
    },
    toolSummary: {
      getDocument: 'ドキュメントを取得: {title}',
      document: 'ドキュメント',
      listChunks: '{title}を表示',
      listFaqEntry: 'FAQを表示: {question}',
      deepThinking: '深い思考'
    },
    entityLink: {
      kb: 'ナレッジベース',
      doc: 'ドキュメント',
      chunk: 'チャンク'
    },
    citation: {
      notFound: 'コンテンツが見つかりません',
      loadFailed: '読み込みに失敗しました',
      noKbForWiki: '関連するナレッジベースを特定できないため、Wikiを開けません。'
    },
    weknoraDocs: {
      pages: 'ドキュメント {count} 件',
      hits: '一致した節 {count} 件',
      empty: '一致するドキュメントはありません',
      outline: '目次',
      content: '本文',
      truncated: '本文は続きます',
      failed: '読み取れませんでした',
      openDoc: 'ドキュメントサイトで開く'
    },
    operations: {
      found: '実行できる操作 {count} 件',
      unavailableCount: '現在使えない操作 {count} 件',
      empty: '一致する操作はありません',
      unavailableHeading: '現在使えません',
      parameters: 'パラメータ',
      required: '必須',
      enum: '選択肢',
      range: '範囲 {min}–{max}',
      truncated: '結果は省略されています',
      emptyResult: 'データはありません',
      failed: '操作に失敗しました',
      meta: '補足',
      risk: {
        read: '読み取り',
        probe: 'チェック',
        write: '書き込み',
        destructive: '取り消し不可'
      },
      names: {
        session: {
          list: '会話一覧を取得'
        },
        automation: {
          list: '自動化の一覧を取得',
          create: '自動化を作成',
          validate_trigger: '実行時刻を確認',
          get: '自動化の詳細を取得',
          update: '自動化を更新',
          delete: '自動化を削除',
          pause: '自動化を一時停止',
          resume: '自動化を再開',
          run_now: '自動化を今すぐ実行',
          list_runs: '自動化の実行履歴を取得'
        },
        skill: {
          list_installed: 'インストール済みスキル一覧を取得',
          install: 'スキルをインストール',
          get_installed: 'インストール済みスキルの詳細を取得',
          uninstall: 'スキルをアンインストール',
          set_enabled: 'スキルの有効状態を設定',
          list: '実行可能なスキル一覧を取得',
          list_catalog: 'ワークスペースのスキル一覧を取得',
          get_catalog: 'ワークスペースのスキルの詳細を取得',
          install_catalog: 'カタログのスキルをサンドボックスにインストール'
        },
        model: {
          list: 'モデル一覧を取得',
          list_providers: 'モデルプロバイダー一覧を取得',
          get_provider: 'モデルプロバイダーの詳細を取得',
          get: 'モデルの詳細を取得',
          delete: 'モデルを削除',
          update: 'モデルの表示情報を更新',
          copy: 'モデル設定をコピー'
        },
        message: {
          chat_history_stats: 'チャット履歴の統計を取得',
          search: '会話履歴を検索',
          list: 'メッセージ履歴を取得'
        },
        mcp_service: {
          list: 'MCP サービス一覧を取得',
          create: 'MCP サービスを作成',
          get: 'MCP サービスの詳細を取得',
          update: 'MCP サービスを更新',
          delete: 'MCP サービスを削除',
          test: 'MCP サービスの接続をテスト',
          list_tools: 'MCP ツールをリアルタイムで取得',
          get_metadata: '同期済み MCP ツールを表示',
          refresh_metadata: 'MCP ツール一覧を同期'
        },
        web_search_provider: {
          list: 'ウェブ検索サービス一覧を取得',
          get: 'ウェブ検索サービス詳細を取得',
          list_types: 'ウェブ検索サービスの種類を取得',
          test: 'ウェブ検索接続をテスト',
          update: 'ウェブ検索サービスを更新',
          delete: 'ウェブ検索サービスを削除'
        },
        system: {
          get_info: 'バージョンとシステム情報を取得'
        },
        workspace: {
          get: '現在のワークスペース情報を取得',
          update: '現在のワークスペース情報を変更',
          list_members: '現在のワークスペースのメンバーを取得'
        },
        system_admin: {
          list_admins: 'システム管理者を取得',
          list_users: 'プラットフォームユーザーを取得',
          list_settings: 'システム設定を取得',
          get_queues: 'タスクキューの稼働状況を取得',
          list_tasks: 'キューのタスクを取得'
        },
        wiki: {
          list_folders: 'Wiki フォルダー一覧を取得',
          create_folder: 'Wiki フォルダーを作成',
          list_issues: 'Wiki ページの問題一覧を取得',
          lint: 'Wiki ページを検査',
          move_page: 'Wiki ページを移動',
          get_page: 'Wiki ページを取得',
          rebuild_links: 'Wiki リンクを再構築',
          revert: 'Wiki ページの版を復元',
          list_revisions: 'Wiki ページの版一覧を取得',
          get_stats: 'Wiki の統計を取得'
        },
        knowledge: {
          list: 'ナレッジ一覧を取得',
          list_folders: 'ナレッジフォルダー一覧を取得',
          rename_folder: 'フォルダーの名前変更または移動',
          create_manual: 'ナレッジを手動作成',
          create_from_url: 'URL からナレッジを作成',
          batch_delete: 'ナレッジを一括削除',
          batch_reparse: 'ナレッジを一括再解析',
          move_to_folder: 'ナレッジをフォルダーに移動',
          update_manual: '手動作成したナレッジを更新',
          move: 'ナレッジを別のナレッジベースに移動',
          get_move_progress: 'ナレッジの移動状況を取得',
          set_tags: 'ナレッジのタグを設定',
          get: 'ナレッジの詳細を取得',
          update: 'ナレッジを更新',
          delete: 'ナレッジを削除',
          cancel_parse: 'ナレッジの解析をキャンセル',
          reparse: 'ナレッジを再解析',
          get_parse_progress: 'ナレッジの解析状況を取得'
        },
        faq: {
          batch_update: 'FAQ の状態とタグを一括更新',
          list_entries: 'FAQ 項目一覧を取得',
          delete_entries: 'FAQ 項目を一括削除',
          get_entry: 'FAQ 項目の詳細を取得',
          update_entry: 'FAQ 項目を更新',
          add_similar_questions: '類似の質問を追加',
          create_entry: 'FAQ 項目を作成'
        },
        knowledge_base: {
          list_parser_engines: '利用可能な解析エンジンを取得',
          copy: 'ナレッジベースの内容をコピー',
          duplicate: 'ナレッジベースの設定をコピー',
          get_copy_progress: 'ナレッジベースのコピー進捗を取得',
          list: 'ナレッジベース一覧を取得',
          create: 'ナレッジベースを作成',
          get: 'ナレッジベースの詳細を取得',
          delete: 'ナレッジベースを削除',
          update: 'ナレッジベースを更新',
          list_activity: 'ナレッジベースの操作履歴を取得',
          search: 'ナレッジベースを検索',
          list_move_targets: '移動先のナレッジベース一覧を取得',
          generate_profile: 'ナレッジベースの説明を生成',
          list_tags: 'ナレッジベースのタグ一覧を取得',
          create_tag: 'ナレッジベースのタグを作成',
          update_tag: 'ナレッジベースのタグを更新',
          delete_tag: 'ナレッジベースのタグを削除',
          list_shared: '共有ナレッジベース一覧を取得'
        },
        chunk: {
          get: 'チャンク詳細を取得',
          update: 'チャンクを更新',
          list_revisions: 'チャンクの変更履歴を取得',
          revert: 'チャンクの過去の版を復元',
          list: 'ナレッジチャンク一覧を取得'
        },
        artifact: {
          list: '生成ファイル一覧を取得'
        },
        agent: {
          list: 'エージェント一覧を取得',
          create: 'エージェントを作成',
          get: 'エージェントの詳細を取得',
          delete: 'エージェントを削除',
          update: 'エージェントを更新',
          copy: 'エージェントをコピー'
        },
        data_source: {
          list: 'データソース一覧を取得',
          get: 'データソース詳細を取得',
          test: 'データソースの接続をテスト',
          sync: 'データソースを同期',
          pause: 'データソースの同期を一時停止',
          resume: 'データソースの同期を再開',
          list_sync_logs: 'データソースの同期履歴を取得',
          get_sync_log: 'データソースの同期進捗を取得',
          list_resources: '同期可能なリソースを取得',
          update_sync: 'データソースの同期設定を更新'
        }
      }
    },
    shellExec: {
      workDir: 'ディレクトリ',
      exitCode: '終了コード',
      stdout: '標準出力',
      stderr: '標準エラー',
      emptyOutput: '出力なし',
      truncated: '出力は省略されています',
      killed: 'タイムアウトにより終了しました',
      binarySuppressed: 'バイナリ出力は省略されました。ダウンロードするには、成果物ディレクトリにファイルを書き込んでください。'
    },
    sandboxFiles: {
      found: '{count}件のファイルが見つかりました',
      empty: 'ファイルなし',
      truncated: '一覧は省略されています',
      wrote: '書き込み済み',
      replacements: '{count}箇所を置換',
      moreLines: '他{count}行'
    },
    imageView: {
      summary: '「{file}」の画像 {numbers} を確認しました（全 {total} 枚）',
      single: '画像「{file}」を確認しました',
      descriptionsHeading: 'ビジョンモデルによる画像の説明',
      imageLabel: '画像 #{n}',
      noDescription: '説明を生成できませんでした',
      remaining: '未確認の画像があと {count} 枚あります'
    },
    attachmentTarget: {
      list: 'すべての添付ファイル',
      file: '添付ファイル',
      images: '{name} の画像',
      imagesUnnamed: '添付ファイルの画像',
      image: '{name} の画像 {n}',
      imageUnnamed: '添付ファイルの画像 {n}'
    },
    skillFiles: {
      heading: 'スキルファイル',
      script: 'スクリプト',
      instructions: 'スキル説明'
    },
    openPage: {
      open: '開く',
      retired: '提供終了',
      openForm: '開いて入力',
      opened: 'アシスタントが開きました',
      back: '戻る',
      endpoint: '接続先：',
      draftHint: 'アシスタントが入力済みです。API キーなどの認証情報を入力し、確認してからご自身で保存してください。'
    },
    pageEdit: {
      title: '{count} か所に入力しました',
      undo: '元に戻す',
      undone: '入力を元に戻しました',
      undoSkipped: '{count} か所は変更済みかページにないため、そのままにしました',
      unsaved: 'まだ保存されていません。確認してからページで保存してください。'
    },
    pageAccess: {
      viewed: '現在のページを確認しました：{location}'
    },
    collaboration: {
      tabs: 'タスクタブ',
      updates: '更新 {count} 件',
      mainConversation: 'メインチャット',
      assignment: 'タスク内容',
      title: 'サブタスク',
      unnamed: '無名のタスク',
      phase: {
        tool_running: 'ツールを使用中',
        tool_succeeded: 'ツール完了',
        tool_failed: 'ツール失敗'
      },
      status: {
        queued: '待機中',
        running: '実行中',
        waiting: '入力待ち',
        succeeded: '完了',
        failed: '失敗',
        interrupted: '中断',
        cancelled: 'キャンセル済み',
        needs_attention: '対応が必要',
        cancelling: 'キャンセル中',
        unknown: '不明'
      }
    },
    tools: {
      searchKnowledge: 'ナレッジベース検索',
      grepChunks: 'テキストパターン検索',
      webSearch: 'Web検索',
      webFetch: 'Webページ取得',
      getDocumentInfo: 'ドキュメント情報を取得',
      listKnowledgeChunks: 'ナレッジチャンクを一覧表示',
      getRelatedDocuments: '関連ドキュメントを検索',
      getDocumentContent: 'ドキュメント内容を取得',
      wikiReadSourceDoc: 'ソースドキュメントを精読',
      readDocument: 'ドキュメントを読む',
      listDocuments: 'ドキュメント一覧',
      todoWrite: '計画管理',
      askUser: 'ユーザーに質問',
      requestSecureForm: '認証情報をリクエスト',
      browserFillSecret: '認証情報を入力',
      knowledgeGraphExtract: 'ナレッジグラフ抽出',
      thinking: '思考',
      attachmentParsing: '添付ファイルを解析',
      imageAnalysis: '画像解析',
      queryUnderstand: 'クエリを理解',
      queryKnowledgeGraph: 'ナレッジグラフ照会',
      readSkill: 'スキルを読み取り',
      executeSkillScript: 'スキルスクリプトを実行',
      listSandboxFiles: 'サンドボックスのファイル一覧',
      readFile: 'ファイルを読み取り',
      readSandboxFile: 'サンドボックスのファイルを読み取り',
      writeSandboxFile: 'サンドボックスにファイルを書き込み',
      editSandboxFile: 'サンドボックスのファイルを編集',
      shellExec: 'サンドボックスコマンドを実行',
      dataAnalysis: 'データ分析',
      dataSchema: 'データスキーマ',
      databaseQuery: 'データベース照会',
      findOperations: '操作を検索',
      runOperation: '操作を実行',
      spawn_agent: 'エージェントを起動',
      list_agents: 'エージェント一覧',
      send_message: 'メッセージを送信',
      followup_task: 'タスクを続行',
      interrupt_agent: 'エージェントを中断',
      wait_agent: 'エージェントを待機',
      openPage: 'ページを開く',
      viewPage: 'ページを確認',
      searchWeKnoraDocs: '製品ドキュメントを検索',
      readWeKnoraDoc: '製品ドキュメントを読む',
      readPage: 'ページを確認',
      selectTab: 'タブを選択',
      fillPage: 'ページに入力'
    },
    mcpOAuth: {
      waiting: '認可待ち · {target}',
      waitingStatus: '認可待ち',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '続行するには {target} を認可してください',
      titleWithService: 'OAuth · {service}',
      titleWithTool: 'OAuth · {service} › {tool}',
      desc: '認可すると、サインイン用の新しいウィンドウが開きます。認可が成功すると、ツール呼び出しは自動的に再開されます。',
      authorize: '認可',
      skip: 'スキップ',
      countdownShort: '{seconds}秒',
      authorizedTag: '認可済み',
      timedOutTag: '認可がタイムアウトしました',
      canceledTag: 'キャンセル済み',
      authorizedToast: '認可しました。再開しています…',
      startFailed: '認可の開始に失敗しました',
      resumeFailed: '再開に失敗しました。再試行してください。',
      skipFailed: 'スキップに失敗しました。再試行してください。'
    },
    hostReview: {
      denied: '自動審査で拒否：{reason}'
    },
    hostApproval: {
      command: 'コマンド',
      grantPath: 'アクセス先',
      accessWrite: '読み書き',
      accessRead: '読み取り専用',
      firstAttemptRan: 'このコマンドは一度実行して失敗しています。承認するとコマンド全体が再実行されます',
      snippet: '拒否の詳細',
      sessionRules: 'このセッションで許可すると、このディレクトリでの次の削除は再確認しません（ファイル名は異なっても可）',
      reject: '拒否',
      approveOnce: '今回のみ許可',
      approveSession: 'このセッションでは許可',
      approvedOnce: '今回のみ許可しました',
      approvedSession: 'このセッションでは許可済み',
      rejectedTag: '拒否済み',
      submitted: '送信しました',
      submitFailed: '送信に失敗しました',
      userRejected: 'ユーザーが拒否しました',
      fileOnly: 'このファイルだけを許可します',
      writeMode: '方式',
      writeModeOverwrite: '上書き',
      writeModeAppend: '追記',
      writeModeEdit: '編集',
      writeBytes: '{bytes} バイト',
      preview: '内容',
      previewTruncated: '先頭 64 KB のみ表示',
      env: '環境変数',
      skillName: 'スキル',
      stdin: '標準入力',
      script: 'コマンドが実行するスクリプト'
    },
    toolApproval: {
      title: '承認',
      toolDescription: 'ツールの説明',
      delegatedTask: '委任されたタスク',
      waitingStatus: '承認待ち',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '{target} の実行を許可しますか？',
      operationQuestion: '{action}「{target}」を許可しますか？',
      operationQuestionNoTarget: '{action}を許可しますか？',
      operationTarget: '{action}「{target}」',
      characterCount: '{count} 文字',
      argsLabel: '引数',
      argsModified: '変更あり',
      allowInSession: 'この会話では同様の操作をすべて許可',
      countdownShort: '{seconds}秒',
      approve: '承認して実行',
      reject: '拒否',
      approvedTag: '承認済み',
      rejectedTag: '拒否済み',
      parked: 'バックグラウンドで待機中。後で対応できます',
      parkedUntil: 'バックグラウンドで待機中。{time} までに対応してください',
      abandonedTag: '破棄済み',
      canceledTag: 'キャンセル済み',
      invalidJson: '引数は有効なJSONである必要があります',
      submitted: '送信しました',
      submitFailed: '送信に失敗しました',
      userRejected: 'ユーザが拒否しました',
      value: {
        document: 'ドキュメント',
        faq: 'FAQ',
        wiki: 'Wiki',
        on: 'オン',
        off: 'オフ',
        vector: 'ベクトル',
        keyword: 'キーワード',
        graph: 'グラフ',
        quickAnswer: 'クイック回答',
        smartReasoning: 'スマート推論',
        indexSep: '、'
      },
      detail: {
        type: '種類',
        embeddingModel: '埋め込みモデル',
        summaryModel: '要約モデル',
        captionModel: '画像説明',
        speechModel: '音声認識',
        storage: 'ストレージ',
        indexes: 'インデックス',
        name: '名前',
        title: 'タイトル',
        status: '状態',
        summary: '説明',
        model: 'モデル',
        mode: 'モード',
        url: 'リンク',
        from: '移動元',
        to: '移動先',
        folder: 'フォルダ',
        page: 'ページ',
        version: 'バージョン',
        documents: 'ドキュメント',
        knowledgeBases: 'ナレッジベース',
        mcpServices: 'MCP サービス',
        skills: 'スキル',
        webSearch: 'ウェブ検索',
        multiTurn: 'マルチターン',
        transport: 'トランスポート',
        authentication: '認証方式',
        usageInstructions: '利用ガイド',
        displayName: '表示名',
        enabled: '有効',
        sandbox: 'サンドボックス',
        sandboxes: 'サンドボックス',
        systemPrompt: 'システムプロンプト',
        content: '内容',
        kbScope: 'ナレッジベースの範囲',
        mcpScope: 'MCP の範囲',
        skillsScope: 'スキルの範囲'
      },
      grantLapsed: {
        changed: '以前の許可は無効になりました。自動化の Agent 設定、ロール、または権限上限が変更されました。',
        expired: '以前の許可は期限切れです。',
        idle: '以前の許可は長期間使われなかったため無効になりました。'
      }
    },
    promptDock: {
      approvalTitle: '承認が必要です',
      oauthTitle: '認可が必要です',
      secureFormTitle: '認証情報の入力が必要です',
      waiting: 'あなたの対応待ち',
      handle: '対応する',
      pager: '{current} / {total}',
      previous: '前へ',
      next: '次へ',
      collapse: '折りたたむ',
      expand: '展開'
    },
    secureForm: {
      onlyFillInto: '入力先：{domains} のみ',
      observedAt: 'ブラウザの現在のページ：{origin}',
      originUnknown: 'ブラウザの現在のページを確認できません。ログインするサイトが表示されていることを確認してください',
      originMismatch: 'ブラウザの現在のページ（{origin}）はログイン先のサイトと一致しません。確認してから入力してください',
      originInsecure: 'ブラウザのページが HTTPS ではないため、認証情報は入力されません',
      savedAccount: '保存済みアカウント',
      useNew: '新しいユーザー名とパスワードを使う',
      username: 'ユーザー名',
      password: 'パスワード',
      saveToVault: '保管庫に保存',
      useOnce: '今回のみ使用',
      fill: '入力',
      decline: '拒否',
      submittedHidden: '送信済み（内容は非表示）',
      declined: '拒否しました',
      timedOut: 'タイムアウト',
      canceled: 'キャンセルされました',
      submitFailed: '送信に失敗しました',
      savedButClosed: '認証情報は保管庫に保存されましたが、このリクエストはすでに終了しています'
    },
    askUser: {
      answerLabel: 'あなたの回答',
      title: 'あなたへの質問',
      selectPlaceholder: '選択してください',
      textPlaceholder: '回答を入力',
      otherPlaceholder: 'その他（任意）',
      decline: '回答しない',
      submit: '送信',
      declinedTag: '回答を辞退しました',
      submitted: '送信済み',
      answeredTag: '回答済み',
      timedOutTag: '時間内に回答なし',
      canceledTag: 'キャンセル済み',
      unansweredTag: '未回答',
      submitFailed: '送信に失敗しました'
    }
  },
  kbSettings: {
    parser: {
      title: '解析エンジン',
      description: 'ファイル形式ごとにドキュメントの解析エンジンを選択します。未設定のファイル形式には組み込みの解析エンジンが使用されます。',
      loading: '読み込み中...',
      noEngineAvailable: '利用できる解析エンジンがないか、ドキュメント解析サービスが設定されていません。',
      default: 'デフォルト',
      goConfig: '設定へ移動 →',
      noEngine: '利用可能なエンジンがありません',
      fileTypePdf: 'PDFドキュメント',
      fileTypeWord: 'Wordドキュメント',
      fileTypePpt: 'プレゼンテーション',
      fileTypeExcel: 'Excelスプレッドシート',
      xlsxFirstRowAsHeader: '先頭行を列見出しとして扱い、各行のコンテキストに保持する',
      fileTypeEbook: '電子書籍',
      fileTypeWebArchive: 'Webアーカイブ',
      fileTypeCsv: 'CSVファイル',
      fileTypeText: 'プレーンテキスト',
      fileTypeJson: 'JSONファイル',
      fileTypeImage: '画像',
      fileTypeAudiovisual: '音声',
      engines: {
        opendataloader: {
          name: 'OpenDataLoader',
          desc: 'OpenDataLoader PDF解析エンジン（レイアウト解析。Java 11以上とopendataloader-pdfが必要）'
        },
        markitdown: {
          name: 'MarkItDown',
          desc: 'Microsoft MarkItDownコンバータ（PDF/Office/HTMLなど）'
        },
        paddleocr_vl_cloud: {
          name: 'PaddleOCR-VL Cloud',
          desc: 'PaddleOCR-VL Cloud API'
        },
        paddleocr_vl: {
          name: 'PaddleOCR-VL',
          desc: 'PaddleOCR-VLセルフホストサービス'
        },
        mineru_cloud: {
          name: 'MinerU Cloud',
          desc: 'MinerU Cloud API'
        },
        mineru: {
          name: 'MinerU',
          desc: 'MinerUセルフホストサービス'
        },
        anydoc: {
          name: 'anydoc',
          desc: 'プロセス内で動作するOfficeドキュメントの解析エンジン（外部サービス不要）'
        },
        simple: {
          name: 'シンプル',
          desc: 'シンプルな形式と画像の解析（外部サービス不要）'
        },
        builtin: {
          name: '組み込み',
          desc: 'DocReader組み込み解析エンジン（docx/pdf/xlsxなどの複雑な形式に対応）'
        }
      }
    },
    storage: {
      title: 'ストレージエンジン',
      selectDescription: 'このナレッジベースを紐づけるストレージインスタンスを選択します。',
      defaultTag: 'デフォルト',
      instanceLabel: 'ストレージインスタンス',
      instanceDesc: '同じストレージ種別でも、エンドポイント、バケット、認証情報が異なる複数のインスタンスを持てます。',
      migrateHint: 'このナレッジベースにはすでにファイルが含まれています。インスタンスを切り替えるにはストレージ移行フローを使用してください。',
      manageInstances: 'ストレージインスタンスを管理',
      localStorage: 'ローカルストレージ',
      loading: '読み込み中...'
    },
    vectorStore: {
      title: 'ベクトルストア',
      description: 'このナレッジベースの書き込み先ベクトルストアを選択します。この紐づけは変更できません。既存のナレッジベースを別のストアへ移すには、新しいナレッジベースを作成してインデックスを再作成してください。',
      loading: 'ベクトルストアを読み込み中...',
      engineLabel: 'ベクトルストア',
      engineDesc: 'グローバルのベクトルストア設定からストアを選択します。システムデフォルトのままにすると、ワークスペース全体のRETRIEVE_DRIVERエンジンが使用されます。',
      boundLabel: '紐づけ済みベクトルストア',
      systemDefault: 'システムデフォルト',
      immutableHint: '作成後は変更できません。後から移行するには、目的のストアに紐づけた新しいナレッジベースを作成し、インデックスを再作成してください。',
      immutableEdit: 'ベクトルストアの紐づけは作成後に変更できません。',
      unavailableHint: '紐づけられたベクトルストアは現在利用できません。設定 → ベクトルストアで接続設定を確認してください。',
      goGlobalSettings: 'ベクトルストア設定へ移動'
    }
  },
  vectorStoreBadge: {
    systemDefault: 'システムデフォルト',
    sharedFromOrg: '他の共有スペースから共有',
    unknownStore: '不明なストア',
    unavailable: '利用不可'
  },
  tools: {
    multiKbSearch: 'ナレッジベース横断検索',
    searchKnowledge: 'ナレッジベースを検索',
    readDocument: 'ドキュメントを読む',
    listDocuments: 'ドキュメント一覧',
    knowledgeSearch: 'ナレッジベース検索',
    grepChunks: 'テキストパターン検索',
    getChunkDetail: 'チャンク詳細の取得',
    listKnowledgeChunks: 'ナレッジチャンクの一覧',
    listKnowledgeBases: 'ナレッジベースの一覧',
    getDocumentInfo: 'ドキュメント情報の取得',
    queryKnowledgeGraph: 'ナレッジグラフの照会',
    think: '深い思考',
    todoWrite: '計画の作成'
  },
  commandPalette: {
    placeholder: 'ナレッジベース、ファイル、会話を検索…',
    clearRecent: 'クリア',
    retrieval: '検索設定',
    untitledSession: '無題の会話',
    hotkey: {
      select: '移動',
      enter: '開く',
      cmdNumber: '直接開く',
      cmdEnter: 'チャットを開始',
      esc: '閉じる'
    },
    empty: {
      noResults: '一致する項目がありません',
      askAi: 'AIに直接質問する',
      adjustRetrieval: '検索設定を調整'
    },
    quick: {
      newChat: '新しい会話',
      knowledgeBases: 'ナレッジベースを開く',
      agents: 'エージェントを開く',
      organizations: '共有スペースを開く',
      settings: '設定を開く',
      productTour: 'プロダクトツアー',
      assistant: '{name}を開く'
    },
    match: {
      vector: 'ベクトル',
      keyword: 'キーワード'
    },
    group: {
      chunks: 'ファイル',
      messages: 'メッセージ',
      kbs: 'ナレッジベース',
      agents: 'エージェント',
      sessionsByTitle: 'チャット（タイトル）',
      commands: 'コマンド',
      recent: '最近',
      quickActions: 'クイックアクション'
    },
    scope: {
      placeholder: 'このナレッジベース内を検索…',
      remove: '範囲を解除（Backspace）'
    }
  },
  assistant: {
    title: 'Xiaozhi アシスタント',
    newConversation: '新しい会話',
    history: '会話履歴',
    untitledConversation: '無題の会話',
    historyEmpty: '会話履歴はありません',
    historyFailed: '会話履歴を読み込めませんでした',
    loadMore: 'さらに読み込む',
    resize: 'アシスタントの幅を調整',
    welcomeTitle: '何をお手伝いしましょうか？',
    agentWelcomeDesc: 'このエージェントの設定を確認したり、モデルを変更したり、検索可能なナレッジベースを確認できます。',
    welcomeDesc: 'Xiaozhi の使い方、ナレッジやドキュメントの整理、エージェント・ツール・自動化の設定をお手伝いします。',
    startFailed: 'アシスタントを起動できませんでした。もう一度お試しください。',
    chooseAction: '機能を選ぶか、希望する内容を入力してください。',
    askAboutAnswer: 'この回答について{name}に聞く',
    starters: {
      agentConfig: 'このエージェントの設定はどこを改善できますか？',
      agentModel: 'このエージェントにはどのモデルが向いていますか？',
      agentKnowledge: 'どのナレッジベースを検索できる？',
      wikiIssues: 'この Wiki ページで補足や確認が必要な内容は何ですか？',
      wikiSummary: 'この Wiki ページの要点は何ですか？',
      documentSummary: 'このドキュメントの重要な結論は何ですか？',
      recentActivity: '最近アップロードまたは更新されたドキュメントはどれですか？',
      agents: 'これらのエージェントはそれぞれどんな質問に向いていますか？',
      messageSources: 'この回答の根拠は何ですか？',
      messageCheck: 'この回答に誤りはありますか？',
      modelCheck: 'このモデルの設定は現在の用途に合っていますか？',
      modelUsage: 'どのエージェントとナレッジベースがこれらのモデルを使っていますか？',
      mcpTools: 'この MCP サービスにはどんなツールがありますか？',
      mcpCheck: 'このサービスを使うには他に何を設定すべきですか？',
      modelSetup: 'ほかにどのモデルを設定する必要がありますか？',
      mcpSetup: 'MCP サービスを接続するには？',
      releaseHighlights: '現在のバージョンでは主に何が変わりましたか？',
      gettingStarted: 'Xiaozhi を初めて使う場合、何から設定すればよいですか？',
      workflow: 'ナレッジベース、エージェント、自動化はどう組み合わせて使えますか？',
      knowledgeOverview: 'それぞれのナレッジベースでどんな情報を探せますか？',
      knowledgeType: 'ドキュメント、FAQ、Wiki はどう使い分ければよいですか？',
      knowledgeOrganize: '手元の資料を使いやすいナレッジベースに整理するには？',
      knowledgeTopics: 'これらのドキュメントはそれぞれ何についてですか？',
      knowledgeGaps: '解析に失敗した、またはまだ完了していないドキュメントはどれですか？',
      faqCoverage: 'これらの FAQ はどんなよくある質問をカバーしていますか？',
      faqDuplicates: '内容が重複していて統合できる FAQ はありますか？',
      faqImprove: '補足や更新が必要な回答はどれですか？',
      documentSteps: 'このドキュメントの手順を、そのまま実行できる手順に整理して',
      documentFaq: 'このドキュメントからどんな FAQ を作れますか？',
      wikiSources: 'この Wiki ページの結論を裏付ける情報源は何ですか？',
      agentCreate: 'ナレッジベースを検索できるエージェントはどう作りますか？',
      agentChoose: 'ナレッジベースを調べるなら、ここのどのエージェントを使えばよいですか？',
      automationIdeas: '繰り返し行う作業のうち、何を自動化できますか？',
      automationCreate: 'ナレッジベースの更新を毎週まとめるタスクを設定して',
      automationOverview: '最近の自動化タスクはどのように実行されていますか？',
      automationSummary: 'このタスクの直近の実行で何が生成されましたか？',
      automationSchedule: 'このタスクは次にいつ実行されますか？',
      automationImprove: 'このタスクのプロンプトと実行スケジュールをどう改善できますか？',
      skillFind: 'ここのスキルのうち、エージェントに追加する価値があるものは？',
      skillAdd: '新しいスキルを追加してエージェントで有効にするには？',
      skillUse: '追加済みの各スキルで何ができますか？',
      mcpFind: 'これらの MCP サービスで、エージェントが呼べるツールはどれですか？',
      mcpExamples: 'エージェントにこれらの MCP ツールを使わせるには？',
      mcpUsage: 'このサービスのツールの使い方を例で見せて',
      modelFit: 'このモデルはどんなタスクに向いていますか？',
      modelTypes: 'チャット、埋め込み、リランキングのモデルはどう選べばよいですか？',
      browserConnect: 'エージェントが使えるようにブラウザを接続するには？',
      browserTasks: 'ブラウザでどんな Web 操作を自動化できますか？',
      browserReconnect: 'ブラウザがオフラインと表示されたら、どう再接続しますか？',
      messageReuse: 'この回答を、そのまま実行できる手順にして',
      chatSummary: 'この会話では何を尋ね、どんな結果が得られましたか？',
      chatCheck: '直近の回答に漏れや誤りはありませんか？',
      chatFollowup: 'この会話を踏まえて、次にどんな質問ができますか？',
      artifactRecent: '最近生成されたファイルはどれですか？',
      artifactSources: 'これらのファイルはそれぞれどの会話から来ましたか？',
      artifactCreate: 'エージェントに結果をファイルとして保存させるには？',
      organizationShared: 'これらの共有スペースには、それぞれどのナレッジベースとエージェントがありますか？',
      organizationJoin: '既存の共有スペースに参加するには？',
      organizationCreate: '共有スペースを作成してメンバーを招待するには？'
    },
    context: {
      currentPage: '現在のページ',
      detach: '現在のページを含めない',
      attachedTip: '現在のページを含めています：{path}',
      detachedTip: 'クリックして現在のページを含める：{path}',
      chatMessage: 'この回答',
      pages: {
        knowledge_base: 'ナレッジベース',
        wiki: 'Wiki',
        agent_editor: 'エージェント編集',
        settings_models: 'モデル管理',
        mcp_services: 'MCP サービス',
        settings: '設定',
        chat: 'チャット'
      }
    },
    access: {
      title: '権限レベル',
      capped: 'ワークスペース管理者が許可していません',
      levels: {
        auto_write: {
          label: '自動実行',
          desc: '元に戻せる変更はそのまま実行し、削除は確認します'
        },
        confirm: {
          label: '変更前に確認',
          desc: '変更や削除のたびに事前に確認します'
        },
        read_only: {
          label: '読み取り専用',
          desc: '確認だけで、何も変更しません'
        }
      },
      page: {
        label: '現在のページの確認と入力',
        desc: '左側のページを読み取り、フォームに入力できます。ボタンのクリックや保存はしません。'
      }
    },
    fillNotice: {
      title: 'アシスタントが {count} か所に入力しました',
      undo: '元に戻す',
      dismiss: '閉じる'
    },
    bubble: {
      label: 'アシスタントの操作',
      ask: 'アシスタントに聞く',
      polish: '推敲',
      rewrite: '書き直し',
      translate: '翻訳',
      continue: '続きを書く',
      prompts: {
        polish: '選択したテキストを推敲してください。誤字や不自然な表現を直し、意味は変えずにその場で置き換えてください。',
        rewrite: '選択したテキストを、より明確で簡潔な表現に書き直し、その場で置き換えてください。',
        translate: '選択したテキストを翻訳してください。中国語は英語に、その他の言語は中国語にして、その場で置き換えてください。',
        continue: '選択したテキストの後に、文脈に合う段落を一つ書き足してください。'
      }
    },
    selection: {
      label: '選択中',
      lines: '{count} 行を選択',
      detach: '選択内容を含めない',
      tip: '送信時に選択内容を含めます：{text}',
      tipField: '送信時に「{field}」の選択内容を含めます：{text}'
    },
    prompts: {
      createAgent: '次の要望でエージェントを作成してください：{request}。利用可能なモデル、ナレッジベース、MCP、スキルを確認して選び、必要な不足情報だけを質問してください。現在の権限に従い、作成後に編集画面を開いてください。',
      createAutomation: '定期タスクを作成してください：{request}。指定がなければタイムゾーンは {timezone}。単独実行できる指示にまとめ、日時を検証し次回の実行時刻を示してください。権限を引き上げず現在の規則に従い、作成後にタスクを開いてください。',
      summarizeActivity: '次のフィルター情報の loaded_entry_ids だけを要約してください：{scope}。同じ条件で検索し、必要ならページを追加取得してください。対象資料、実行者、結果を示し、操作ログと本文変更を区別してください。表示済みの記録を全件とみなさないでください。',
      explainMcpTools: 'MCP サービス {id} の保存済みツール一覧を読み、機能と実用的な質問例を3つ示してください。古い情報や不足を明示し、更新、ツール実行、設定変更はしないでください。',
      answerToDocument: '回答と元の質問 {source} を読み、出典と不確実性を保った文書草稿を作成してください。草稿を示して保存先のナレッジベースを確認し、現在の権限で新規作成してください。既存資料は上書きしないでください。',
      answerToFaq: '回答と元の質問 {source} から標準質問と正確な回答を作成してください。草稿を示し、保存先 FAQ ナレッジベースを確認し、類似項目を調べて現在の権限で保存してください。既存項目は上書きしないでください。',
      answerToAutomation: '回答と質問 {source} の反復作業を独立実行できる定期タスクにまとめてください。不足する頻度、時刻、タイムゾーンを確認し、実行予定を検証・表示して現在の権限で作成してください。実行権限は引き上げないでください。',
      writePrompt: '現在のエージェントの目的と設定に基づいてシステムプロンプトを作成してください。目的が不明な場合は先に質問してください。テンプレートのプレースホルダーを保持し、現在のエディターに提案を入力してください。保存済みのエージェントを変更・保存しないでください。',
      refinePrompt: '添付のシステムプロンプトの役割、回答要件、ツールの使用ルールを明確にしてください。元の意図とテンプレートのプレースホルダーを保持し、修正を現在のエディターに入力してください。保存済みのエージェントを変更・保存しないでください。',
      modelFailure: '現在のモデル設定と添付の接続エラーを基に原因を分析し、確認手順を提案してください。認証情報の読み取りや表示、設定の変更や保存は行わないでください。',
      mcpFailure: 'MCP サービス（ID: {id}）を確認し、添付のツール取得または同期エラーの原因と確認手順を説明してください。認証情報の読み取りや表示、再接続、設定変更は行わないでください。',
      syncFailure: 'データソース「{source}」（ID: {id}）の同期ログ（ID: {log}）を確認し、添付のエラー例と失敗件数から原因と対処方法を説明してください。同期の再試行やデータソースの変更は行わないでください。',
      writeWikiRules: '現在のナレッジベースの用途に基づいて「{field}」の明確なルールを作成してください。用途が不明な場合は先に確認してください。対応する入力欄に記入し、システムの引用・出力規約を維持してください。保存や再解析は行わないでください。',
      refineWikiRules: '添付の「{field}」のルールを、意味を保ちながら明確にしてください。対応する入力欄に記入し、システムの引用・出力規約を維持してください。保存や再解析は行わないでください。',
      analyzeChunks: '添付の分割プレビューについて、原文とチャンクの抜粋、実行時のパラメータ、統計から、意味の分断や短すぎる・長すぎるチャンクを分析し、調整案を示してください。抜粋から確認できる問題と追加の原文が必要な判断を区別してください。設定変更やナレッジベースの再構築は行わないでください。'
    },
    actions: {
      summarizeActivity: 'この {count} 件の更新を要約',
      toolExamples: '使用例を見る',
      answerToDocument: '文書にまとめる',
      answerToFaq: 'FAQ として保存',
      answerToAutomation: '定期タスクにする',
      writePrompt: '作成を手伝う',
      refinePrompt: 'プロンプトを改善',
      diagnose: '原因を分析',
      refineRules: 'ルールを改善',
      analyzeChunks: '分割結果を分析'
    },
    create: {
      agentTitle: '自然言語でエージェントを作成',
      agentAction: 'アシスタントで作成',
      agentHint: '利用者と目的を説明してください。アシスタントがリソースを選び、作成します。',
      agentPlaceholder: '例：製品ナレッジベースから質問に回答し、出典を示し、不明な点は説明するサポート担当。',
      automationTitle: 'アシスタントでタスクを作成',
      automationHint: '実行する内容と日時を入力すると、アシスタントが自動化タスクにまとめます。',
      automationPlaceholder: '例：毎週金曜日の午後5時に、製品ナレッジベースの今週の更新をまとめる。',
      requestLabel: 'タスクの説明',
      manual: '手動で設定',
      start: 'アシスタントに依頼'
    },
    settingsPages: {
      memory: {
        description: 'I can tell workspace memory apart from personal memory, and how to keep workspace conventions.',
        q1: 'How is workspace memory different from my personal memory?',
        q2: 'Which memory rules are enabled now?',
        q3: 'How do I make agents remember this workspace’s conventions?'
      },
      mymemory: {
        description: 'I can show your personal memories, where they are used, and how to add or delete them.',
        q1: 'Which personal memories are saved here?',
        q2: 'How do I add or delete a memory?',
        q3: 'Which conversations use these memories?'
      },
      'integration-claw': {
        description: 'I can explain how to connect Xiaozhi to Claw, and which skill to install.',
        q1: 'How do I connect Xiaozhi to Claw?',
        q2: 'Which skill do I need to install?',
        q3: 'What can I do in Claw after it is connected?'
      },
      'integration-chrome': {
        description: 'I can explain what the browser extension does, how to install it, and where selected text goes.',
        q1: 'What can the browser extension do?',
        q2: 'How do I install and sign in to the extension?',
        q3: 'Where does text I select in the extension get sent?'
      },
      'integration-cli': {
        description: 'I can walk you through installing and signing in to the CLI, and the common commands.',
        q1: 'How do I install and sign in to the WeKnora CLI?',
        q2: 'What knowledge-base and chat operations can the CLI do?',
        q3: 'What are the most useful commands?'
      },
      'integration-mcpserver': {
        description: 'I can explain how to expose Xiaozhi as an MCP server, and which tools it offers.',
        q1: 'How do I offer Xiaozhi as an MCP server?',
        q2: 'How does an external client connect?',
        q3: 'Which tools does this server expose?'
      },
      'integration-api': {
        description: 'I can explain how to start a chat over the API, which auth to send, and show an example.',
        q1: 'How do I start a conversation through the API?',
        q2: 'What authentication does a request need?',
        q3: 'Is there a ready-made request example?'
      },
      'integration-embed': {
        description: 'I can explain how to embed the chat widget, and which knowledge bases visitors can use.',
        q1: 'How do I embed the chat widget on my website?',
        q2: 'Which knowledge bases or agents can visitors use?',
        q3: 'Which parameters do I need to change in the embed code?'
      },
      'integration-im': {
        description: 'I can walk you through connecting Feishu or WeCom, and what to check when the bot is silent.',
        q1: 'How do I connect Feishu or WeCom to this workspace?',
        q2: 'How do people use an agent from the IM chat?',
        q3: 'What should I check if the bot is not receiving messages?'
      },
      'system-audit-log': {
        description: 'I can filter audit events, find risky actions, and say how long logs are kept.',
        q1: 'What high-risk actions happened recently?',
        q2: 'How do I filter audit records by person or workspace?',
        q3: 'How long are these logs kept?'
      },
      'platform-api-keys': {
        description: 'I can tell platform keys from workspace keys, and how to create or revoke them.',
        q1: 'What is the difference between a platform API key and a workspace key?',
        q2: 'How do I create a key that can only access one workspace?',
        q3: 'How do I revoke a leaked key immediately?'
      },
      'runtime-queues': {
        description: 'I can show stuck task queues and how to retry failed parse or index jobs.',
        q1: 'Which task queues are stuck right now?',
        q2: 'How do I retry a failed parse or index job?',
        q3: 'How do I see the jobs running in a queue?'
      },
      'model-catalog': {
        description: 'I can browse the model catalog and explain how to add a vendor model to this workspace.',
        q1: 'Which vendors and models can I connect from the catalog?',
        q2: 'How do I add a catalog model to this workspace?',
        q3: 'What is still missing before I can use a vendor?'
      },
      'system-global-other': {
        description: 'I can explain uncategorized global settings and what to watch before changing them.',
        q1: 'What are these uncategorized settings for?',
        q2: 'What does changing one of them affect?',
        q3: 'Which of these should I avoid changing in production?'
      },
      'system-global-security': {
        description: 'I can explain security policy, keys and session switches, and the risk of changing them.',
        q1: 'What does each security switch protect?',
        q2: 'How do I rotate or revoke a platform-level key?',
        q3: 'Which security changes affect users who are already signed in?'
      },
      'system-global-runtime': {
        description: 'I can explain how runtime, task and resource options affect background work.',
        q1: 'Which background tasks do these runtime settings affect?',
        q2: 'How do I limit concurrency or timeouts?',
        q3: 'When do runtime changes take effect?'
      },
      'system-global-tenant': {
        description: 'I can explain workspace policy, default quotas, and what a new workspace inherits.',
        q1: 'What defaults apply when someone creates a workspace?',
        q2: 'How do I limit how many workspaces one person can create?',
        q3: 'What is the default storage quota for a workspace?'
      },
      'system-global-users': {
        description: 'I can list platform users, explain roles, and how to disable or adjust an account.',
        q1: 'Which users are on this platform?',
        q2: 'How do I disable a user or change their permissions?',
        q3: 'How is a system admin different from a regular user?'
      },
      'system-global-access': {
        description: 'I can explain the login, signup and access-control switches.',
        q1: 'What does each access-control switch restrict?',
        q2: 'How do I turn off open signup or limit sign-in methods?',
        q3: 'Do I need to restart the service after changing these?'
      },
      'system-global': {
        description: 'I can walk through this deployment’s global settings, users and workspaces, and security switches.',
        q1: 'Which global settings does this deployment have?',
        q2: 'How do I manage users and workspaces on the platform?',
        q3: 'What do the security switches control?'
      },
      system: {
        description: 'I can tell you the current version, component status, and what to check before an upgrade.',
        q1: 'What version is this, and what changed recently?',
        q2: 'How do I check the status of this deployment’s components?',
        q3: 'What should I review or back up before upgrading?'
      },
      websearch: {
        description: 'I can show configured web-search providers and how to let agents search the web.',
        q1: 'Which web search services are configured?',
        q2: 'How do I give agents web search?',
        q3: 'Where do I put the search API key?'
      },
      sandbox: {
        description: 'I can explain what the sandbox runs, how to add a config, and what to check when scripts fail.',
        q1: 'What is the sandbox used for?',
        q2: 'How do I add a sandbox configuration?',
        q3: 'Which sandbox settings should I check when an agent script fails?'
      },
      storage: {
        description: 'I can explain where files are stored, how to switch to object storage, and what happens at quota.',
        q1: 'Where are uploaded files stored right now?',
        q2: 'How do I switch to object storage?',
        q3: 'What happens when the storage quota is used up?'
      },
      parser: {
        description: 'I can show the default document parser, which formats need another engine, and what to change after a failure.',
        q1: 'Which document parser is the default?',
        q2: 'Which file formats need a different parser?',
        q3: 'What should I change when document parsing fails?'
      },
      vectorstore: {
        description: 'I can explain the current vector engine, what changing it does, and how to check it.',
        q1: 'Which vector search engine is in use now?',
        q2: 'Will changing the engine affect existing knowledge bases?',
        q3: 'How do I check that the search engine is working?'
      },
      ollama: {
        description: 'I can walk you through connecting local Ollama and adding its models to this workspace.',
        q1: 'How do I connect a local Ollama instance?',
        q2: 'How do I add its models to this workspace after connecting?',
        q3: 'What should I check if Ollama will not connect?'
      },
      chathistory: {
        description: 'I can tell you whether chat-history search is on, what it can find, and how to build the index.',
        q1: 'Is chat-history search turned on?',
        q2: 'What past conversations can it search after I turn it on?',
        q3: 'How do I index past conversations?'
      },
      members: {
        description: 'I can list members and roles, explain invites, and what each role can do.',
        q1: 'Who is in this workspace, and what are their roles?',
        q2: 'How do I invite a new member?',
        q3: 'What can an admin do that a regular member cannot?'
      },
      tenant: {
        description: 'I can show this workspace’s name, quota and basic info, and what you can edit.',
        q1: 'What is this workspace’s name and storage quota?',
        q2: 'How do I change the workspace name or description?',
        q3: 'What happens when storage is almost full?'
      },
      envvars: {
        description: 'I can explain where these environment variables are used, and how personal values differ from workspace ones.',
        q1: 'Which skills or agents use these environment variables?',
        q2: 'How do I fill in my own secrets safely?',
        q3: 'What is the difference between workspace and personal variables?'
      },
      assistant: {
        description: 'I can explain the assistant entry points, permission levels, and what it may or may not do for you.',
        q1: 'What does each assistant permission level mean?',
        q2: 'How do I put the assistant in the sidebar or the corner?',
        q3: 'Can the assistant change settings or delete things for me?'
      },
      userprofile: {
        description: 'I can help review and update your account profile, and explain what happens after a change.',
        q1: 'Where do I change my account details?',
        q2: 'How do I change my avatar, name or password?',
        q3: 'Do I need to sign in again after updating my account?'
      },
      general: {
        description: 'I can explain language, theme and other personal preferences, and where they apply.',
        q1: 'Which parts of the UI do these preferences affect?',
        q2: 'How do I change the language or theme?',
        q3: 'Which personal settings should I set up first?'
      },
      fallback: {
        description: 'I can explain what this settings page does, what a change affects, and what to configure first.',
        q1: 'What is this settings page for?',
        q2: 'What will change if I edit these options?',
        q3: 'Which settings should I configure first?'
      }
    },
    welcomeDescriptions: {
      knowledgeBases: 'ナレッジベースの種類選びや資料の整理、質問に合った情報源探しをお手伝いします。',
      knowledgeBase: 'これらのドキュメントが何を扱っているか、最近の更新、まだ解析が終わっていないファイルを整理します。',
      document: 'ドキュメントの要点や操作手順を整理したり、内容から FAQ を作成したりできます。',
      faq: 'FAQ の網羅性や質問の重複を確認し、回答をより分かりやすくするお手伝いをします。',
      wiki: 'ページの要点や引用元を確認し、補足や更新が必要な箇所を見つけるお手伝いをします。',
      agents: '実現したいことを教えてください。適切なモデル、ナレッジベース、ツールを備えたエージェントの作成をお手伝いします。',
      automation: '繰り返しの作業を定期タスクにしたり、実行結果の確認やスケジュールの調整をお手伝いしたりできます。',
      skills: 'タスクの目的を教えてください。スキルを探して追加し、適切なエージェントで使えるよう設定するお手伝いをします。',
      mcp: 'MCP サービスの検索と接続、利用できるツールの確認、エージェントでの利用設定をお手伝いします。',
      browser: 'ブラウザの接続方法、自動化に適したタスク、必要な権限をご案内します。',
      model: 'モデルの接続や用途の比較、タスクに合った設定の確認をお手伝いします。',
      chat: 'この会話で何を尋ね、何が得られたかを要約し、最新の回答を確認し、次に何を聞くかを提案できます。',
      message: 'この回答の出典や重要な情報を確認し、再利用しやすい内容に整理するお手伝いをします。',
      artifacts: 'これらのファイルを日時や種類で整理し、どの会話から来たかを探し、エージェントに結果をファイルとして保存させる方法を説明できます。',
      organizations: '各共有スペースで使えるナレッジベースとエージェント、作成・参加・招待の方法をご案内します。'
    },
    help: {
      label: 'アシスタントの説明',
      title: 'Xiaozhi アシスタントにできること',
      identity: 'アシスタントはあなた自身として動きます。見たり変更したりできる範囲は、このスペースでのあなたの役割までです。',
      page: '開くと現在のページが付きます。画面の内容を整理したり、エージェントや自動化を設定したり、フォームに記入したりできます。ボタンを押したり保存したりはしません。',
      access: '入力欄の下で権限を切り替えられます。閲覧のみ、変更前に確認、回復できる変更は自動実行。削除は必ず確認が必要で、管理者が定めた上限は超えられません。'
    },
    layout: {
      dock: '右側に固定',
      float: 'フローティング表示にする'
    }
  },
  preview: {
    loading: 'ドキュメントのプレビューを読み込み中...',
    loadFailed: 'ドキュメントのプレビューの読み込みに失敗しました',
    retry: '再試行',
    unsupported: 'このファイル形式はオンラインプレビューに対応していません',
    unsupportedHint: 'ダウンロードして、ローカルのアプリケーションで開いてください',
    zoomIn: '拡大',
    zoomOut: '縮小',
    fullscreen: '全画面表示',
    exitFullscreen: '全画面表示を終了',
    htmlRendered: 'レンダリング表示',
    htmlSource: 'ソースを表示',
    audioNotSupported: 'お使いのブラウザは音声再生に対応していません',
    videoNotSupported: 'お使いのブラウザは動画再生に対応していません'
  },
  organization: {
    owner: '作成者',
    roleUpdated: 'ロールを更新しました',
    roleUpdateFailed: 'ロールの更新に失敗しました',
    createdByMe: '自分が作成',
    joinedByMe: '自分が参加',
    share: {
      title: '共有スペースへ共有',
      selectOrg: '共有スペースを選択',
      selectOrgPlaceholder: '共有先の共有スペースを選択',
      permission: '権限',
      permissionTip: '編集可能な権限ではメンバーがナレッジベースの内容を変更できます。読み取り専用の権限では検索と質問応答のみ行えます',
      shareSuccess: 'ナレッジベースを共有しました',
      shareFailed: '共有に失敗しました',
      unshareSuccess: '共有を解除しました',
      unshareFailed: '共有の解除に失敗しました',
      sharedTo: '共有先',
      noShares: 'まだどの共有スペースにも共有されていません',
      searchPlaceholder: '共有スペースを検索…',
      loading: '読み込み中…',
      emptySearch: '「{q}」に一致する共有スペースがありません',
      addShareDialogTitle: '共有スペースへ共有',
      unshareAction: '共有を解除',
      sharedFrom: '共有元',
      permissionReadonly: '読み取り専用',
      permissionEditable: '編集可能',
      columns: {
        space: '共有スペース',
        permission: '権限',
        sharedAt: '共有日',
        operations: '操作'
      }
    },
    settings: {
      pendingJoinRequestsBadge: '確認が必要な参加申請があります'
    },
    role: {
      admin: '管理者',
      editor: '編集者',
      viewer: '閲覧者'
    },
    join: {
      title: '共有スペースに参加'
    }
  },
  promptTemplate: {
    noTemplates: '利用できるテンプレートがありません',
    selectTemplate: 'テンプレートを選択',
    useTemplate: 'テンプレートを使用',
    resetDefault: 'デフォルトに戻す',
    default: 'デフォルト',
    withKnowledgeBase: 'ナレッジベース',
    withWebSearch: 'Web検索'
  },
  mcpServiceDialog: {
    addTitle: 'MCPサービスを追加',
    addDesc: '外部の MCP サービスを接続すると、エージェントがそのツールを呼び出せます。',
    editTitle: 'MCPサービスを編集',
    basicSection: '基本',
    connectionSection: '接続',
    enableServiceDesc: 'オフの場合、このサービスは呼び出されません',
    unitSecond: '秒',
    name: 'サービス名',
    namePlaceholder: 'サービス名を入力してください',
    transportType: 'トランスポート種別',
    serviceUrl: 'サービスURL',
    serviceUrlPlaceholder: 'https://example.com/mcp',
    enableService: 'サービスを有効化',
    authConfig: '認証',
    authType: '認証方式',
    authTypeNone: 'なし／カスタムヘッダー',
    authTypeApiKey: 'APIキー／トークン',
    authTypeOAuth: 'OAuth 2.0（初回接続時に認可）',
    oauthScopes: 'スコープ（任意、スペース区切り）',
    oauthClientId: 'クライアント ID（任意）',
    oauthClientIdDesc: '認可サーバーに事前登録したクライアントを指定します。空欄の場合は動的クライアント登録で自動登録します。クライアント ID を変更する場合はシークレットも更新してください。',
    oauthClientSecret: 'クライアントシークレット（任意）',
    oauthAuthorization: '認可状態',
    oauthAuthorized: '認可済み',
    oauthRefreshable: 'トークンの有効期限が切れています。次回利用時に自動的に更新されます',
    oauthUnauthorized: '未認可',
    oauthAuthorize: '認可',
    oauthReauthorize: '再認可',
    oauthRevoke: '認可を取り消す',
    oauthAuthorizeHint: '「認可」をクリックすると現在の設定を保存してから認可を開始します（ユーザごとに個別に認可します）。',
    apiKeyHeader: 'ヘッダー名',
    apiKeyHeaderDesc: '未入力の場合はX-API-Keyが使われます。Bearerの場合はAuthorizationを指定し、下の値に「Bearer <token>」を入力してください。生トークンを使うサービスではAuthorizationに生トークンを設定します。',
    credentialValue: 'シークレット／トークン',
    optional: '任意',
    advancedConfig: '詳細設定',
    timeoutSec: 'タイムアウト（秒）',
    codeImport: {
      toggle: 'コードからインポート',
      hint: '標準のmcpServers JSON設定を貼り付けるとフォームに自動入力されます',
      parse: '解析して入力',
      editOverwriteHint: 'インポートすると現在のフォームが上書きされます（保存済みの認証情報は影響を受けません。適用するには保存をクリックしてください）',
      toasts: {
        filled: 'フォームに入力しました。内容を確認して保存してください',
        multipleServers: '複数のサービスが見つかったため、最初の1件をインポートしました: {name}'
      },
      errors: {
        empty: '先に設定を貼り付けてください',
        invalidJson: '解析できません。JSONの形式を確認してください',
        noServer: 'MCPサービスの設定が見つかりません',
        missingUrl: '設定にurlがありません',
        stdioUnsupported: 'stdio（command/args）の設定には対応していません。urlを含むリモート設定を使用してください'
      }
    },
    customHeaders: {
      label: 'カスタムヘッダー（任意）',
      desc: 'すべてのMCPリクエストに付与されるHTTPヘッダーです。企業向けゲートウェイの認証やトレースなどに利用します。',
      add: 'ヘッダーを追加',
      keyPlaceholder: 'ヘッダー名',
      valuePlaceholder: 'ヘッダーの値'
    },
    toasts: {
      updated: 'MCPサービスを更新しました',
      updateFailed: 'MCPサービスの更新に失敗しました',
      authorized: '認可が完了しました',
      authorizeFailed: '認可の開始に失敗しました',
      revoked: '認可を取り消しました',
      revokeFailed: '認可の取り消しに失敗しました'
    },
    rules: {
      nameRequired: 'サービス名を入力してください',
      transportRequired: 'トランスポート種別を選択してください',
      urlRequired: 'サービスURLを入力してください',
      urlInvalid: '有効なURLを入力してください'
    }
  },
  mcpMetadata: {
    searchTools: 'ツール名や説明を検索',
    retry: '再試行',
    details: '詳細',
    description: '説明',
    parameters: 'パラメーター',
    required: '必須',
    fullSchema: '完全な定義',
    noDescription: '説明はありません',
    noParameters: 'パラメータ定義はありません',
    enabled: '有効',
    approval: '承認が必要',
    noTools: '該当するツールはありません',
    next: '次へ',
    policyLoadFailed: 'ツール設定を読み込めません。編集前に再試行してください。',
    policySaveFailed: 'ツール設定を保存できませんでした',
    tools: 'Tools 一覧',
    cacheHint: '未同期の場合はこの手順で自動接続して保存します。以降は更新時のみ MCP サーバーに接続します。',
    fetch: '再取得',
    fetching: '接続して Tools を取得しています…',
    toolCount: '{count} 件のツール',
    stale: '接続または認証設定が変更されました。モデルで使用する前に一覧を更新してください。',
    notSynced: '未同期です。取得すると説明とパラメーター定義が保存されます。',
    syncRequired: '先に接続して Tools を取得してください。モデルは同期済みの一覧のみ使用できます。',
    syncedAt: '同期日時：',
    serverDocumentation: 'サーバーの元の説明',
    noServerDocumentation: 'この MCP サーバーの initialize に instructions / serverInfo.description はありません（どちらも任意）。ツールの説明は下の各 description にあります。',
    policyHint: 'ツールの有効化と承認設定は即時保存され、一覧の更新後も維持されます。',
    columnTool: 'ツール',
    columnEnabled: '有効',
    columnApproval: '承認',
    failed: 'ツール一覧を読み込めませんでした',
    setupProgress: 'MCP 設定の手順',
    connection: '接続設定',
    toolsAndUsage: 'ツールと用途',
    previous: '戻る',
    usage: 'サービスの用途',
    usageHint: 'モデルはこの概要を読んでから必要なツールを読み込みます。更新しても入力内容は保持されます。',
    usageInstructions: '使用方法',
    instructionsPlaceholder: 'サービスの用途、利用場面、重要な制約を簡潔に記載してください。',
    generateUsage: 'AI で生成',
    generateHint: '同期済みの有効なツールから簡潔な説明を生成します。編集して保存すると反映されます。',
    instructionsRequired: '使用方法を入力してください',
    generated: '生成しました。内容を確認して保存してください。',
    generateFailed: '生成に失敗しました。ツールの同期と利用可能なチャットモデルの設定を確認して再試行してください。'
  },
  ollamaSettings: {
    installed: {
      title: 'インストール済みモデル',
      desc: 'Ollamaにインストールされているモデル'
    },
    download: {
      title: 'モデルをダウンロード'
    },
    address: {
      desc: 'ローカルのOllamaサービスのAPIアドレスです。システムが自動検出します。変更するには.envファイルで設定してください。'
    },
    status: {
      desc: 'ローカルのOllamaサービスが利用可能かを自動検出します。サービスが停止しているかURLが誤っている場合は「利用不可」と表示されます。'
    }
  },
  modelSettings: {
    moreActions: 'その他の操作',
    title: 'モデル設定',
    copySuffix: ' のコピー',
    builtinTag: '組み込み',
    confirmDelete: 'モデル「{name}」を削除しますか？',
    debug: {
      reasoningEffort: '思考強度',
      reasoningEffortDesc: 'モデルカタログが報告するレベルで reasoning_effort を送信します',
      title: 'モデルテスト',
      description: '保存済みのモデル設定でリクエストを送信します。編集中の変更は保存後に反映されます。',
      groupModel: 'モデルを選択',
      groupInput: 'テスト入力',
      groupResult: '結果',
      modelType: 'モデルの種類',
      model: 'モデル',
      modelPlaceholder: 'テストするモデルを選択',
      noModelsForType: 'この種類の保存済みモデルはありません',
      query: '入力',
      queryPlaceholder: 'モデルに送信するテキストを入力してください',
      embeddingInput: '埋め込み対象のテキスト',
      embeddingPlaceholder: '埋め込みを生成するテキストを入力してください',
      vlmPrompt: '画像プロンプト',
      vlmPromptPlaceholder: '例: この画像を詳しく説明してください',
      documents: '候補ドキュメント',
      documentsPlaceholder: '候補ドキュメントを1行に1件ずつ入力してください',
      documentsHint: '空でない各行が個別のドキュメントとしてリランクモデルに送信されます',
      imageFile: '画像ファイル',
      similarityMode: '類似度',
      similarityQuery: 'クエリ',
      similarityQueryPlaceholder: 'クエリを入力（例：芝生を走る犬）',
      similarityCandidates: '候補テキスト',
      similarityCandidatesPlaceholder: '候補テキストを1行に1件ずつ入力してください',
      similarityHint: 'クエリは検索クエリとして、候補はドキュメントとしてベクトル化されます（実際の検索と同じ）。結果はコサイン類似度の高い順に並びます',
      similarityImage: '候補画像（任意）',
      similarityImageCandidate: '画像',
      audioFile: '音声ファイル',
      chooseFile: 'ファイルを選択',
      parameters: 'リクエストパラメータ',
      systemPrompt: 'システムプロンプト',
      systemPromptPlaceholder: 'システムプロンプト（任意）',
      run: 'テストを実行',
      copyResult: '結果をコピー',
      history: '履歴',
      runLabel: '実行 #{n}',
      success: 'リクエストに成功しました',
      failed: 'リクエストに失敗しました',
      rawResponse: '応答',
      requestPreview: 'リクエストのプレビュー',
      requestFailed: 'モデルテストのリクエストに失敗しました',
      metrics: {
        api: 'プロトコル',
        thinkingFormat: '思考形式',
        requestedReasoningEffort: '要求した強度',
        dimension: '次元数',
        resultCount: '結果件数',
        answerChars: '回答文字数',
        reasoningChars: '推論文字数',
        reasoningReturned: '推論内容の返却',
        textChars: '文字起こし文字数',
        segmentCount: 'セグメント数'
      }
    },
    usage: {
      title: 'モデルを削除できません',
      description: 'モデル「{name}」は次の設定から参照されています。削除する前に各設定を開き、別のモデルを選択してください。',
      knowledgeBases: 'ナレッジベース（{count}）',
      agents: 'エージェント（{count}）',
      openConfiguration: '設定を開く',
      truncated: '{total}件中の最初の{shown}件を表示',
      longTermMemory: '長期メモリ'
    },
    builtinModels: {
      title: '組み込みモデル',
      description: '組み込みモデルはすべてのワークスペースに表示されます。機密情報は非表示で、編集や削除はできません。',
      descriptionAdmin: '組み込みモデルはすべてのワークスペースに表示されます。システム管理者は設定と認証情報を編集できますが、削除はデプロイ側で管理されます。',
      viewGuide: '組み込みモデルのガイドを見る'
    },
    toasts: {
      nameRequired: 'モデル名を入力してください',
      nameTooLong: 'モデル名は100文字以内で入力してください',
      displayNameTooLong: '表示名は100文字以内で入力してください',
      baseUrlRequired: 'リモートAPIにはBase URLが必要です',
      baseUrlInvalid: 'Base URLが正しくありません。有効なURLを入力してください',
      dimensionInvalid: '埋め込み次元数は128〜4096の範囲で指定してください',
      updated: 'モデルを更新しました',
      added: 'モデルを追加しました',
      saveFailed: 'モデルの保存に失敗しました',
      deleted: 'モデルを削除しました',
      deleteFailed: 'モデルの削除に失敗しました',
      builtinCannotEdit: '組み込みモデルは編集できません',
      linkedModelMissing: 'アシスタントがリンクしたモデルが見つかりません。削除された可能性があります',
      builtinCannotDelete: '組み込みモデルは削除できません',
      builtinCannotCopy: '組み込みモデルはコピーできません',
      copied: 'モデルをコピーしました',
      copyFailed: 'モデルのコピーに失敗しました'
    },
    asr: {
      title: 'ASR音声モデル',
      desc: '音声の文字起こしに使用する音声認識モデルを設定します（例: OpenAI Whisper）',
      empty: 'ASRモデルがありません'
    },
    vllm: {
      title: 'VLLM視覚モデル',
      desc: 'マルチモーダル理解に使用する視覚言語モデルを設定します',
      empty: 'VLLMモデルがありません'
    },
    rerank: {
      title: 'リランクモデル',
      desc: '結果のリランクに使用するモデルを設定します',
      empty: 'リランクモデルがありません'
    },
    embedding: {
      title: '埋め込みモデル',
      desc: 'テキストのベクトル化に使用する埋め込みモデルを設定します',
      empty: '埋め込みモデルがありません'
    },
    chat: {
      title: 'チャットモデル',
      desc: '会話に使用する大規模言語モデルを設定します',
      empty: 'チャットモデルがありません'
    },
    source: {
      remote: 'リモート',
      openaiCompatible: 'OpenAI互換',
      custom: 'カスタム'
    },
    actions: {
      addModel: 'モデルを追加',
      debugModel: 'モデルテスト'
    },
    typeShort: {
      chat: 'チャット',
      embedding: '埋め込み',
      rerank: 'リランク',
      vllm: '視覚',
      asr: '音声'
    }
  },
  mcpSettings: {
    addUsageInstructions: '使用方法を追加',
    noUsageInstructions: '使用方法は未入力です',
    title: 'MCPサービス',
    description: 'エージェントモードでツールやリソースを利用するための外部MCP（Model Context Protocol）サービスを管理します',
    enabled: '有効',
    disabled: '無効',
    addService: 'サービスを追加',
    empty: 'MCPサービスがありません',
    deleteConfirmBody: 'MCPサービス「{name}」を削除しますか？この操作は取り消せません。',
    unnamed: '名称未設定',
    builtin: '組み込み',
    toolCount: '{count} 個のツール',
    toolsNotSynced: 'ツール未同期',
    toolsStale: '再同期が必要',
    toasts: {
      loadFailed: 'MCPサービスの読み込みに失敗しました',
      enabled: 'MCPサービスを有効化しました',
      disabled: 'MCPサービスを無効化しました',
      updateStateFailed: 'MCPサービスのステータス更新に失敗しました',
      linkedServiceMissing: 'アシスタントがリンクした MCP サービスが見つかりません。削除された可能性があります',
      deleted: 'MCPサービスを削除しました',
      deleteFailed: 'MCPサービスの削除に失敗しました'
    }
  },
  conversationSettings: {
    maxTokens: {
      desc: '応答で生成するトークンの最大数'
    },
    temperature: {
      desc: '出力のランダム性を制御します。0が最も決定的で、1が最もランダムです'
    },
    systemPrompt: {
      desc: '通常モードの会話で使用するシステムレベルのプロンプト'
    },
    contextTemplate: {
      desc: '通常モードで検索結果に基づき回答を生成するためのプロンプトテンプレート'
    },
    rerankModel: {
      desc: '検索結果のリランクに使用するモデル（任意）'
    },
    chatModel: {
      desc: '要約や概要の生成に使用する大規模言語モデル'
    },
    rewritePrompt: {
      desc: 'クエリリライト時に使用するシステムプロンプト'
    },
    fallbackPrompt: {
      desc: 'フォールバック戦略が「モデル」の場合に使用するプロンプト'
    },
    fallbackResponse: {
      desc: '固定フォールバック戦略を使用する場合に返すテキスト'
    },
    fallbackStrategy: {
      desc: '関連するドキュメントが見つからない場合の応答方法'
    },
    enableQueryExpansion: {
      desc: 'リコールが低い場合に推論モデルを呼び出して拡張クエリを生成します（レイテンシとコストが増加します）'
    },
    enableRewrite: {
      desc: 'マルチターンのクエリを自動的にリライトし、リコールを向上させます'
    },
    rerankThreshold: {
      desc: 'リランク後に必要な最小スコア'
    },
    rerankTopK: {
      desc: 'リランク後に保持するドキュメント数'
    },
    vectorThreshold: {
      desc: 'ベクトル検索の最小類似度'
    },
    keywordThreshold: {
      desc: 'キーワード検索の最小スコア'
    },
    embeddingTopK: {
      desc: 'ベクトル検索後に保持するドキュメント数'
    },
    maxRounds: {
      desc: 'コンテキストとクエリリライトのために保持する会話ターン数'
    },
    models: {
      chatGroupLabel: '思考／チャットモデル'
    }
  },
  agentSettings: {
    systemPrompt: {
      desc: 'エージェントのシステムプロンプトを設定します。プレースホルダは実行時に実際の内容へ自動的に置き換えられます。'
    },
    allowedTools: {
      desc: '現在エージェントで有効になっているツール'
    },
    temperature: {
      desc: '出力のランダム性を制御します。0が最も決定的で、1が最もランダムです'
    },
    rerankModel: {
      desc: '検索結果をリランクし、関連度スコアを正規化します'
    },
    thinkingModel: {
      desc: 'エージェントの推論と計画に使用するLLM'
    },
    maxIterations: {
      desc: '1つのタスクで実行できる推論ステップ数の上限です。無制限の場合、モデルが自ら停止するか手動で停止するまで実行を続けます。'
    },
    modelRecommendation: {
      title: '推奨モデル'
    }
  },
  uploadTasks: {
    panelLabel: 'アップロード',
    titleUploading: 'アップロード中 {done}/{total}',
    titleParsing: '解析中 {done}/{total}',
    titleDone: 'すべて完了',
    titleDoneWithIssues: '{ok}件完了、{bad}件未完了',
    titleCancelled: 'アップロードをキャンセルしました',
    destination: 'アップロード先：{name}',
    destinationMany: 'アップロード先：{count}件のナレッジベース',
    remaining: '残り約{time}',
    hintUploading: 'アップロードが完了するまでページを閉じたり再読み込みしたりしないでください',
    hintParsing: 'すべてのファイルをアップロードしました。解析はバックグラウンドで続くため、このページを離れても問題ありません',
    filterAll: 'すべて',
    filterIssues: '未完了',
    phaseWaiting: 'アップロード待ち',
    phaseSaving: '保存中…',
    phasePending: '解析待ち',
    phaseReady: '完了',
    phaseParseFailed: '解析失敗',
    phaseDuplicate: '同じファイルが既にあります',
    phaseCancelled: 'キャンセル済み',
    cancel: 'キャンセル',
    cancelAll: 'すべてキャンセル',
    retry: '再試行',
    retryFailed: '{count}件を再試行',
    open: '開く',
    collapse: '折りたたむ',
    expand: '展開',
    close: '閉じる',
    closeConfirm: '閉じると、残り{count}件のアップロードがキャンセルされます',
    closeConfirmOk: 'アップロードをキャンセル',
    closeConfirmKeep: 'アップロードを続ける',
    legend: {
      ready: '検索可能',
      active: '処理中',
      waiting: '待機中',
      failed: '失敗',
      duplicate: '既存'
    },
    eta: {
      seconds: '{n}秒',
      minutes: '{n}分',
      hours: '{n}時間'
    }
  },
  upload: {
    uploadDocument: 'ドキュメントをアップロード',
    uploadFolder: 'フォルダをアップロード',
    onlineEdit: 'オンライン編集',
    deleteRecord: '記録を削除'
  },
  time: {
    today: '今日',
    yesterday: '昨日',
    last7Days: '過去7日間',
    last30Days: '過去30日間',
    lastYear: '過去1年',
    earlier: 'それ以前',
    pinned: 'ピン留め'
  },
  platform: {
    multimodalParsing: 'マルチモーダルドキュメント解析',
    hybridSearchEngine: 'ハイブリッド検索 + ナレッジグラフ',
    ragQandA: 'ReActエージェントQ&A',
    independentTenant: '独立したワークスペース',
    fullApiAccess: 'フルAPIアクセス',
    knowledgeBaseManagement: 'ナレッジベース管理',
    loginShowcase: {
      carouselLabel: '任我行ナレッジベースの機能イメージ',
      switchLabel: '機能テーマを切り替える',
      pause: 'スライドとフローを一時停止',
      play: 'スライドとフローを再生',
      reducedMotion: '動きを減らす設定に従い自動再生を停止',
      labels: {
        query: '質問',
        sourceHit: '原文を検索',
        citedAnswer: '引用付き回答',
        sourceMaterial: '元の資料',
        productKnowledge: '製品知識',
        delivery: '導入支援',
        customerService: 'サポート',
        documents: '文書',
        webContent: 'Web',
        existingKnowledge: '既存の知識',
        knowledgeEntry: '知識の入口',
        materialsReceived: '集約完了',
        contentChange: '内容の変更',
        knowledgeReview: 'レビュー',
        knowledgeUpdate: '知識の更新',
        updateConfirmed: '更新を確認'
      },
      themes: {
        review: {
          title: '変化に合わせて知識を更新',
          description: '内容の変更をレビューし、知識を活用し続ける',
          summary: '変更内容をレビューして確認した後、対応する知識を更新します。',
          mobile: '内容の変更 → レビュー → 知識の更新',
          tab: 'レビューと更新'
        },
        intake: {
          title: '社内資料を一か所に',
          description: '文書、Webページ、既存のナレッジ基盤をつなぐ',
          summary: '文書、Webページ、既存の知識を共通のナレッジ入口に集約します。',
          mobile: '文書 / Web / 既存の知識 → 共通の入口',
          tab: '資料の集約'
        },
        organization: {
          title: '分散した文書をつなぐ',
          description: '資料をテーマ別に整理し、関連する知識をつなぐ',
          summary: '資料を製品知識、導入支援、顧客サポートのテーマに整理します。',
          mobile: '資料 → 製品 / 導入 / サポートの知識',
          tab: '知識の整理'
        },
        query: {
          title: 'すべての回答に根拠を',
          description: '自然な言葉で質問し、出典のある回答へ',
          summary: '質問に関連する原文を検索し、回答と引用を表示します。',
          mobile: '質問 → 原文を検索 → 引用付き回答',
          tab: '引用付き回答'
        }
      }
    }
  },
  font: {
    uiFont: 'インターフェースフォント',
    uiFontDescription: 'メニュー、本文、ボタンなど、ほとんどのUIテキストに使用されるフォントです',
    monoFont: 'コードフォント',
    monoFontDescription: 'コードブロック、ターミナルコマンド、APIキー、ファイルパスなどの技術的なテキストに使用されます。すべての文字が同じ幅のため、0とO、1とlを見分けやすくなります。',
    selectFont: 'フォントを選択',
    sansPreview: 'サンプルSample書体Font — Aa Gg Oo 0123',
    monoPreview: 'const msg = \'Hello\'; // 0O1l',
    fontSize: 'フォントサイズ',
    fontSizeDescription: 'インターフェース全体（文字、アイコン、余白）を拡大縮小し、すぐに反映されます',
    size: {
      small: '小',
      normal: '標準',
      large: '大'
    },
    mono: {
      system: 'システムデフォルト',
      menlo: 'Menlo',
      monaco: 'Monaco',
      consolas: 'Consolas',
      cascadia: 'Cascadia Code',
      'dejavu-mono': 'DejaVu Sans Mono',
      'liberation-mono': 'Liberation Mono',
      monospace: '汎用等幅'
    },
    sans: {
      system: 'システムデフォルト',
      pingfang: 'PingFang SC',
      georgia: 'Georgia（セリフ）',
      yahei: 'Microsoft YaHei',
      times: 'Times New Roman（セリフ）',
      'noto-cjk': 'Noto Sans CJK',
      'dejavu-serif': 'DejaVu Serif（セリフ）',
      'sans-serif': '汎用サンセリフ'
    }
  },
  theme: {
    theme: 'テーマ',
    themeDescription: 'インターフェースの表示テーマを選択します。システム設定に合わせた自動切り替えにも対応しています',
    light: 'ライト',
    dark: 'ダーク',
    system: 'システムに従う',
    selectTheme: 'テーマを選択'
  },
  general: {
    title: '一般設定',
    personalSettings: '個人設定',
    description: '言語や外観などの基本オプションを設定します',
    close: '設定を閉じる'
  },
  language: {
    zhCN: '简体中文',
    zhTW: '繁体字中国語',
    enUS: 'English',
    ruRU: 'Русский',
    koKR: '한국어',
    jaJP: '日本語',
    selectLanguage: '言語を選択',
    language: '言語',
    languageDescription: 'インターフェースの表示言語を選択します',
    languageSaved: '言語設定を保存しました'
  },
  model: {
    modelName: 'モデル名',
    defaultTag: 'デフォルト',
    addModelInSettings: 'モデルを追加するにはシステム設定を開いてください',
    loadFailed: 'モデル一覧の読み込みに失敗しました',
    selectModelPlaceholder: 'モデルを選択',
    builtinTag: '組み込み',
    editor: {
      legacyLocalUnavailable: 'Legacy Ollama service management is retired. The saved record is preserved. To use a local model, select API and enter its OpenAI-compatible endpoint.',
      maxOutputTokensLabel: '最大出力トークン',
      maxOutputTokensPlaceholder: '空欄でカタログ既定値',
      maxOutputTokensDesc: '1 回の応答の出力上限。空欄ならこのモデルのカタログ既定値を使用します。',
      addTitle: 'モデルを追加',
      editTitle: 'モデルを編集',
      sectionType: 'モデルタイプ',
      typeLabel: 'モデルタイプ',
      sectionSource: 'ソース',
      sectionProvider: 'プロバイダ設定',
      sectionAdvanced: '詳細オプション',
      sourceLabel: 'モデルのソース',
      sourceRemote: 'API',
      baseUrlLabel: 'ベースURL',
      displayNameLabel: '表示名（任意）',
      displayNamePlaceholder: '例: サポートQA用モデル',
      displayNameDesc: 'UIでの表示にのみ使用されます。実行時の呼び出しには上のモデル名が使われます。',
      baseUrlPlaceholder: '例: https://api.openai.com/v1',
      baseUrlPlaceholderVllm: '例: http://localhost:11434/v1',
      baseUrlPlaceholderAsr: '例: https://api.openai.com/v1',
      apiKeyOptional: 'APIキー（任意）',
      apiKeyPlaceholder: 'APIキーを入力してください',
      customHeadersLabel: 'カスタムリクエストヘッダー（任意）',
      customHeadersDesc: 'リモートモデルAPIへのリクエストに追加するHTTPヘッダーです（企業ゲートウェイの認証やトレースなどに利用）。Authorization / Content-Typeなどの予約ヘッダーは無視されます。',
      customHeadersAdd: 'ヘッダーを追加',
      customHeadersKeyPlaceholder: 'ヘッダー名',
      customHeadersValuePlaceholder: 'ヘッダーの値',
      testing: 'テスト中...',
      testConnection: '接続をテスト',
      dimensionLabel: 'ベクトル次元数',
      dimensionPlaceholder: '例: 1536',
      dimensionOverrideLabel: '出力次元数のカスタマイズ',
      dimensionOverrideDesc: 'プロバイダのドキュメントでこのモデルがdimensionsパラメータに対応していると記載されている場合にのみ有効にしてください。デフォルトでは検出された実際の次元数のみを使用します。',
      supportsVisionLabel: '視覚・マルチモーダルに対応',
      supportsVisionDesc: 'モデルが画像やマルチモーダル入力を受け付けるかどうか',
      embeddingImageInputLabel: '画像入力',
      embeddingImageInputDesc: 'モデルが画像をテキストと同じベクトル空間に埋め込めるかどうか。カタログ内のモデルは自動判定され、カスタムモデルは手動で宣言します',
      contextWindowLabel: 'コンテキストウィンドウ',
      contextWindowPlaceholder: '提供元の総コンテキスト長を入力',
      contextWindowDesc: '1回のリクエストの総コンテキスト長です。詳細設定の spec が優先され、空欄で spec も未設定の場合は不明と表示します。提供元の実際の上限を入力してください。エージェントは出力トークンと圧縮用の余裕を確保します。',
      contextWindowUnknown: '不明',
      contextWindowTokens: '{count}トークン',
      maxConcurrencyLabel: 'バックグラウンドの並列実行上限',
      maxConcurrencyPlaceholder: '0 = グローバルのデフォルト値を使用',
      maxConcurrencyDesc: 'このモデルへのバックグラウンド（取り込み・エンリッチメント）呼び出しの並列数を制限します。モデルごとにすべてのレプリカで共有されます。0または空欄の場合はグローバルのデフォルト値が使われます。対話型のチャットには影響しません。',
      fillModelAndUrl: '先にモデル識別子とベースURLを入力してください',
      remoteBaseUrlRequired: 'リモートAPIタイプではベースURLが必要です',
      unsupportedModelType: '未対応のモデルタイプです',
      saveAndClose: '保存して閉じる',
      testDraftHint: '保存せずに、現在入力されている接続設定をテストします。',
      testDraftEditHint: '現在の接続設定と、個別に保存された API キーを使用してテストします。',
      testStale: '設定が変更されました。もう一度テストしてください。',
      connectionSuccess: '接続に成功しました',
      connectionFailed: '接続に失敗しました',
      connectionConfigError: '接続に失敗しました。設定を確認してください',
      providerLabel: 'プロバイダ',
      providerPlaceholder: 'モデルプロバイダを選択',
      providerDocs: '{provider} のモデルドキュメントを見る',
      validation: {
        extraFieldRequired: '{name} を入力してください',
        modelNameRequired: 'モデル名を入力してください',
        modelNameEmpty: 'モデル名は空にできません',
        modelNameMax: 'モデル名は100文字以内で入力してください',
        baseUrlRequired: 'ベースURLを入力してください',
        baseUrlEmpty: 'ベースURLは空にできません',
        baseUrlInvalid: 'ベースURLが無効です。有効なURLを入力してください'
      },
      modelNamePlaceholder: {
        remote: '例: gpt-4, claude-3-opus',
        remoteVllm: '例: gpt-4-vision-preview',
        remoteAsr: '例: whisper-1'
      },
      description: {
        chat: '会話用の大規模言語モデルを設定します',
        embedding: 'テキストのベクトル化に使う埋め込みモデルを設定します',
        rerank: '検索結果のリランクに使うモデルを設定します',
        vllm: 'マルチモーダル理解に使う視覚言語モデルを設定します',
        asr: '音声の文字起こしに使う音声認識モデルを設定します',
        default: 'モデル情報を設定します'
      },
      advanced: {
        toggle: '詳細設定',
        compat: {
          label: 'プロトコル互換上書き（JSON）',
          placeholder: '{\'{\'} "max_tokens_field": "max_tokens" {\'}\'}',
          desc: 'エンドポイントの挙動がカタログ既定値と異なる場合のみ、変更するフィールドだけを記入します。空欄で上書きなし。',
          docLink: 'フィールドの説明',
          invalid: 'JSON が不正です',
          mustBeObject: 'JSON オブジェクトが必要です'
        },
        legacyThinking: {
          label: '思考パラメータ形式（旧設定）',
          catalog: 'カタログ既定に従う（推奨）',
          none: '思考パラメータを送信しない',
          desc: 'このモデルには旧版の thinking_control 設定が残っています。「カタログ既定に従う」を選ぶとカタログが決定します。'
        },
        remoteModelName: {
          label: 'リモートモデル名',
          placeholder: '空欄でモデル名と同じ',
          desc: '上のモデル名と異なる場合に、実際にベンダーへ送るモデル ID。'
        },
        api: {
          label: 'プロトコル上書き',
          auto: '自動（ベンダー / URL から推定）',
          desc: 'リクエストプロトコルを強制します。通常は変更不要です。'
        }
      },
      resolved: {
        title: '実際の呼び出し方',
        empty: 'ベンダーとモデル名を入力すると、このモデルの呼び出し方を表示します',
        failed: '解決に失敗',
        protocol: 'リクエストプロトコル',
        catalog: '能力の取得元',
        catalogedYes: '内蔵モデルプロファイル',
        catalogedNo: 'ベンダー既定（カタログ未収録）',
        endpoint: 'リクエスト先',
        thinkingFormat: '思考切替の送り方',
        thinkingLevels: '選択できる思考強度',
        noThinking: 'このモデルは思考できません'
      },
      catalog: {
        reasoning: '推論',
        vision: '画像',
        hint: 'ベンダーのカタログから選ぶか、カスタムのモデル名を入力できます。'
      }
    }
  },
  error: {
    networkError: 'ネットワークエラーです。接続を確認してください',
    invalidCredentials: 'ユーザ名またはパスワードが正しくありません',
    tokenRefreshFailed: 'トークンの更新に失敗しました',
    pleaseRelogin: '再度ログインしてください',
    fileSizeExceeded: 'ファイルサイズは{size}MB以下にしてください！',
    unsupportedFileType: '未対応のファイル形式です！',
    invalidImageLink: '無効な画像リンクです',
    tokenNotFound: 'ログイントークンが見つかりません。再度ログインしてください',
    streamFailed: 'ストリーム接続に失敗しました',
    initialization: {
      checkFailed: 'チェックに失敗しました',
      testFailed: 'テストに失敗しました'
    },
    tenant: {
      listFailed: 'ワークスペース一覧の取得に失敗しました',
      searchFailed: 'ワークスペースの検索に失敗しました',
      getApiPrincipalConfigFailed: 'APIプリンシパル設定の取得に失敗しました',
      updateApiPrincipalConfigFailed: 'APIプリンシパル設定の更新に失敗しました',
      createApiPrincipalTestTokenFailed: 'APIテストトークンの作成に失敗しました',
      updateFailed: 'ワークスペース情報の更新に失敗しました',
      deleteFailed: 'ワークスペースの削除に失敗しました'
    },
    model: {
      createFailed: 'モデルの作成に失敗しました',
      getFailed: 'モデルの取得に失敗しました',
      updateFailed: 'モデルの更新に失敗しました',
      deleteFailed: 'モデルの削除に失敗しました'
    },
    auth: {
      loginFailed: 'ログインに失敗しました',
      registerFailed: '登録に失敗しました',
      getUserFailed: 'ユーザ情報の取得に失敗しました',
      getTenantFailed: 'ワークスペース情報の取得に失敗しました',
      updatePreferencesFailed: '個人設定の更新に失敗しました',
      refreshTokenFailed: 'トークンの更新に失敗しました',
      logoutFailed: 'ログアウトに失敗しました',
      validateTokenFailed: 'トークンの検証に失敗しました'
    }
  },
  mcp: {
    testResult: {
      title: 'テスト結果: {name}'
    }
  },
  system: {
    globalSettings: {
      title: 'システム設定',
      audit: {
        action: {
          'system.setting_changed': 'システム設定の変更',
          'system.admin_promoted': 'システム管理者の付与',
          'system.api_key_created': 'プラットフォームAPIキーの作成',
          'system.api_key_revoked': 'プラットフォームAPIキーの取り消し',
          'system.admin_revoked': 'システム管理者の解除',
          'system.user_password_reset': 'ユーザパスワードのリセット',
          'system.user_created': 'ユーザの作成',
          'system.queue_task_retried': '失敗タスクの再実行',
          'system.queue_task_deleted': '失敗タスクのレコード削除',
          'system.queue_task_run_now': 'キュータスクの即時実行',
          'system.queue_task_cancelled': 'キュータスクの中止',
          'system.queue_archived_purged': '失敗タスクの一括削除'
        },
        actorRole: {
          system_admin: 'システム管理者'
        }
      },
      listConfirm: {
        ssrf: {
          whitelist: {
            remove: {
              header: 'SSRF許可リストから項目を削除',
              body: '{entry}をSSRF許可リストから削除しますか？削除後、この項目は再びSSRF保護によってブロックされます。',
              confirmBtn: '削除'
            },
            add: {
              header: 'SSRF許可リストに項目を追加',
              body: '{entry}をSSRF許可リストに追加しますか？この項目に一致するホスト/IP/CIDRはSSRF保護の対象外となり、エージェントが内部サービスにアクセスできる可能性があります。完全に信頼できる項目のみを追加してください。',
              confirmBtn: '追加'
            }
          }
        }
      },
      enumLabels: {
        auth: {
          default_tenant_mode: {
            create_personal: '個人ワークスペースを作成',
            tenantless: 'ワークスペースを作成しない'
          },
          registration_mode: {
            self_serve: 'セルフサービス（誰でも登録可能）',
            invite_register: '招待リンクでのみ登録可能',
            invite_only: '登録禁止（既存アカウントは招待を承諾可能）'
          }
        }
      },
      keyDescriptions: {
        model: {
          max_concurrency: '単一モデルへのバックグラウンド（取り込み・エンリッチメント）呼び出しのデフォルトの並列実行上限です。モデルIDごとに管理され、すべてのレプリカで共有されます。呼び出しのたびに参照され、再起動なしですぐに適用されます。0または負の値の場合はデフォルトの上限が無効になります（各モデルはモデル管理で設定した独自の上限に従います）。対象はバックグラウンドタスクのみで、対話型のチャットには影響しません。'
        },
        asynq: {
          core_concurrency: 'ドキュメント解析と手動での再解析のプロセスごとの保証並列実行数です。コア解析は共有弾性プールも借用できます。最小値は1で、サービスの再起動が必要です。',
          postprocess_concurrency: 'プロセスごとの並列実行数で、解析完了後の軽量な仕上げ処理とエンリッチメントの振り分け専用です。最小値は1で、サービスの再起動が必要です。',
          enrichment_concurrency: '要約、画像、グラフ、質問の生成のプロセスごとの保証並列実行数です。エンリッチメントは共有弾性プールも借用できます。最小値は1で、サービスの再起動が必要です。',
          maintenance_concurrency: 'データソース同期、一括処理、クリーンアップのプロセスごとの並列実行数で、ユーザ向けのパイプラインから完全に分離されています。最小値は1で、サービスの再起動が必要です。',
          shared_concurrency: 'コア解析とエンリッチメントが共有する、プロセスごとの弾性的な並列実行数です。バックログのある側が自動的に借用します。最小値は1で、サービスの再起動が必要です。',
          wiki_concurrency: 'Wiki専用ワーカプールのプロセスごとの並列実行数で、上流のタスクから分離されています。最小値は1で、サービスの再起動が必要です。'
        },
        tenant: {
          max_owned_per_user: 'スーパーユーザ以外がセルフサービスで所有できるワークスペース数の上限です。ワークスペース作成のたびに参照され、保存後すぐに反映されます。0を指定すると組み込みのデフォルト値10が使われ、負の値を指定すると上限が無効になります（公開環境では非推奨）。',
          self_service_creation_enabled: 'スーパーユーザ以外が自分でワークスペースを作成できるかどうかです。無効にすると、一般ユーザは招待によって既存のワークスペースに参加することしかできません。ワークスペース横断のスーパーユーザは対象外です。すぐに反映されます。',
          default_storage_quota_gb: '新規ワークスペースの作成時に割り当てられるデフォルトのストレージクォータ（GB）です。ベクトル、原本、テキスト、インデックスなどのデータが対象です。作成時にのみ参照されるため、変更は新規作成のワークスペースにのみ適用され、既存のワークスペースには遡って反映されません。0または負の値の場合は組み込みのデフォルト値10GBが使われます。',
          default_storage_quota_mb: '登録時に自動作成される個人スペースにも適用します。正の値はGB設定より優先され、0以下はGB設定を使用します。各設定はデータベース、環境変数、既定値の順に解決し、新規スペースにのみ適用します。',
          auto_create_api_key: '新規ワークスペースにfull_accessのAPIキーを自動作成し、作成レスポンスで平文のトークンを返します。従来の動作に依存する連携でのみ利用してください。デフォルトでは無効で、APIキーは明示的に作成することを推奨します。',
          auto_accept_invitation: '有効にすると、登録済みユーザをメールで招待した際に、受信確認を待たずにすぐメンバーとして追加されます。無効の場合、招待された側がメールから承諾する必要があります。すぐに反映されます。'
        },
        sandbox: {
          docker_enabled: 'Dockerサンドボックスのバックエンドを許可します。ローカルのdocker.sockはホストのroot権限に相当するため、デフォルトでは無効です。有効化できるのはシステム管理者のみで、変更はすぐに反映されます。デーモンのソケットをマウントするプライベートな単一ノード環境、またはTLSで保護されたリモートのtcp://エンドポイントを使用する場合にのみ有効にしてください。'
        },
        ssrf: {
          whitelist: 'SSRF保護の許可リストです。example.com / *.foo.com / 10.0.0.0/8 / 2001:db8::1のような項目を指定できます。保存後すぐに反映されます。SSRF_WHITELIST_EXTRA環境変数は引き続きデプロイ担当者が管理し、ここでは上書きされません。'
        },
        auth: {
          registration_mode: '登録モード。公開登録では誰でもアカウントを作成できます。招待登録には有効な招待リンクが必要です。登録禁止でも既存アカウントは招待を承諾できます。保存後すぐに反映されます。',
          default_tenant_mode: '公開登録後のワークスペース作成方式です。create_personalはオーナー権限のワークスペースを作成し、tenantlessはアカウントのみを作成して、ユーザが招待を承諾するかワークスペースを作成するまで待ちます。新規ユーザにのみ適用されます。',
          complex_password_enabled: '複雑なパスワードを必須にするかどうかです。有効にすると、パスワードに大文字・小文字・数字・特殊文字を含める必要があります。変更はすぐに反映され、新規登録ユーザおよび新たなパスワード変更・リセットにのみ適用されます。特殊文字は{specialChars}です'
        }
      },
      keyLabels: {
        model: {
          max_concurrency: 'モデルごとのデフォルトの並列実行上限'
        },
        asynq: {
          core_concurrency: 'コア解析の保証並列実行数',
          postprocess_concurrency: '後処理の並列実行数',
          enrichment_concurrency: 'エンリッチメントの保証並列実行数',
          maintenance_concurrency: 'メンテナンスの並列実行数',
          shared_concurrency: '共有弾性プールの並列実行数',
          wiki_concurrency: 'Wikiワーカの並列実行数'
        },
        tenant: {
          max_owned_per_user: 'ユーザごとの所有ワークスペース数の上限',
          self_service_creation_enabled: 'ユーザによるワークスペース作成を許可',
          default_storage_quota_gb: '新規ワークスペースのデフォルトストレージクォータ（GB）',
          default_storage_quota_mb: '新規ワークスペースのデフォルトストレージクォータ（MB）',
          auto_create_api_key: '新規ワークスペースにAPIキーを自動作成',
          auto_accept_invitation: '招待した登録済みユーザを自動的に参加させる'
        },
        sandbox: {
          docker_enabled: 'Dockerサンドボックスを有効化'
        },
        ssrf: {
          whitelist: 'SSRF保護の許可リスト'
        },
        auth: {
          registration_mode: '登録モード',
          default_tenant_mode: 'デフォルトのワークスペース作成方式',
          complex_password_enabled: '複雑なパスワードを必須にする'
        }
      },
      runtime: {
        queueDescriptions: {
          default: 'ドキュメント解析、手動での再解析',
          chat_attachment: 'セッション内でアップロードされた添付ファイルの解析',
          postprocess: '解析の最終処理、エンリッチメントの振り分け',
          summary: 'ドキュメントと表の要約',
          sync: '手動およびスケジュール同期',
          low: 'FAQインポート、一括再解析、クリーンアップ',
          multimodal: '画像のOCR、視覚キャプション',
          graph: 'チャンク単位のグラフ抽出',
          question: 'チャンク単位の質問生成',
          wiki: 'コンテンツ生成、インデックスの最終処理'
        },
        queueNames: {
          default: 'ドキュメント解析',
          chat_attachment: 'チャット添付ファイル',
          postprocess: '後処理',
          summary: '要約',
          sync: 'データソース同期',
          low: 'メンテナンスと一括処理',
          multimodal: 'マルチモーダル',
          graph: 'グラフ抽出',
          question: '質問',
          wiki: 'Wikiパイプライン'
        },
        poolDescriptions: {
          core: 'ドキュメント解析と手動での再解析の保証容量',
          postprocess: '解析の最終処理とエンリッチメントの振り分け',
          enrichment: '要約、画像、グラフ、質問の生成',
          maintenance: 'データソース同期、一括処理、削除のクリーンアップ',
          shared: 'バックログに応じてコア解析またはエンリッチメントが借用',
          wiki: 'Wikiコンテンツの生成と全体の最終処理'
        },
        pools: {
          core: 'コア解析',
          postprocess: '後処理オーケストレーション',
          enrichment: 'エンリッチメント',
          maintenance: 'メンテナンスと同期',
          shared: '共有弾性プール',
          wiki: 'Wikiプール'
        },
        tasks: {
          taskTypes: {
            documentProcess: 'ドキュメント解析',
            manualProcess: '手動での再処理',
            temporaryDocumentProcess: 'チャット添付ファイルの解析',
            postProcess: 'ドキュメントの後処理',
            summary: '要約の生成',
            tableSummary: '表の要約の生成',
            question: '質問の生成',
            multimodal: '画像のマルチモーダル処理',
            graph: 'ナレッジグラフの抽出',
            sync: 'データソースの同期',
            faqImport: 'FAQのインポート',
            batchReparse: '一括再解析',
            batchDelete: '一括削除',
            move: 'ドキュメントの移動',
            indexDelete: 'インデックスの削除',
            kbClone: 'ナレッジベースの複製',
            kbDelete: 'ナレッジベースの削除',
            wikiIngest: 'Wikiコンテンツの生成',
            wikiFinalize: 'Wikiの最終処理'
          }
        }
      }
    }
  },
  tenant: {
    title: 'ワークスペース情報',
    currentTenant: '現在のワークスペース',
    switchTenant: 'ワークスペースを切り替え',
    statusActive: 'アクティブ',
    statusInactive: '非アクティブ',
    statusSuspended: '停止中',
    statusUnknown: '不明',
    loadingInfo: '情報を読み込み中...',
    retry: '再試行',
    unknown: '不明',
    formatError: '形式エラー',
    searchPlaceholder: '名前で検索、またはワークスペースIDを入力...',
    noMatch: '一致するワークスペースが見つかりません',
    switchSuccessTitle: 'ワークスペースを切り替えました',
    switchSuccessContent: '{name}に切り替えました',
    loadTenantsFailed: 'ワークスペース一覧の読み込みに失敗しました',
    loading: '読み込み中...',
    api: {
      title: 'API情報',
      userIdLabel: 'ユーザID',
      userIdDescription: 'あなたの一意のユーザ識別子',
      usernameLabel: 'ユーザ名',
      usernameDescription: 'ログイン用のユーザ名',
      createdAtLabel: '登録日時',
      createdAtDescription: 'アカウントが作成された日時'
    },
    messages: {
      fetchFailed: 'ワークスペース情報の取得に失敗しました',
      networkError: 'ネットワークエラーです。しばらくしてから再試行してください'
    },
    deleteDangerZone: {
      title: 'このワークスペースを削除',
      desc: '削除すると、このスペースの個人ファイル、会話、エージェント設定にはアクセスできなくなります。アカウントと共有ナレッジベースは保持されます。',
      button: 'ワークスペースを削除',
      confirmTitle: 'このワークスペースを削除しますか？',
      confirmBody: '「{name}」を削除しますか？ この操作は取り消せません。アカウントと共有ナレッジベースは保持されます。',
      confirmHint: '削除を確認するには、ワークスペース名「{name}」を入力してください。',
      confirm: 'ワークスペースを削除',
      nameMismatch: 'ワークスペース名が一致しません',
      success: 'ワークスペースを削除しました',
      failed: 'ワークスペースの削除に失敗しました'
    },
    leaveDangerZone: {
      title: 'このワークスペースから退出',
      desc: 'このワークスペースのメンバーから外れます。ナレッジベースやエージェントにアクセスできなくなります。後から再度招待を受けることは可能です。',
      button: 'ワークスペースから退出'
    },
    storage: {
      usageLabel: 'ストレージ使用率'
    },
    details: {
      idLabel: 'ワークスペースID',
      nameLabel: 'ワークスペース名',
      descriptionLabel: 'ワークスペースの説明',
      businessLabel: 'ワークスペースの業種',
      statusLabel: 'ワークスペースのステータス',
      createdAtLabel: 'ワークスペースの作成日時',
      editName: '名前を編集',
      editNamePlaceholder: '新しいワークスペース名を入力してください',
      editNameConfirm: '保存',
      editNameCancel: 'キャンセル',
      editNameRequired: 'ワークスペース名は空にできません',
      editNameSuccess: 'ワークスペース名を更新しました',
      editNameFailed: 'ワークスペース名の更新に失敗しました',
      editDescription: '説明を編集',
      editDescriptionPlaceholder: '新しいワークスペースの説明を入力してください',
      editDescriptionSuccess: 'ワークスペースの説明を更新しました',
      editDescriptionFailed: 'ワークスペースの説明の更新に失敗しました',
      descriptionEmptyPlaceholder: '未設定'
    },
    create: {
      action: 'ワークスペースを新規作成',
      dialogTitle: 'ワークスペースを新規作成',
      dialogSubtitle: '個人ファイル用に 10 GB の容量があります。ContextDB のナレッジベースは全アカウントで共有されます。',
      nameLabel: 'ワークスペース名',
      namePlaceholder: '例: 新しいプロジェクト',
      nameRequired: 'ワークスペース名を入力してください',
      descriptionLabel: '説明（任意）',
      descriptionPlaceholder: 'このワークスペースの用途を簡単に入力してください',
      submit: '作成',
      cancel: 'キャンセル',
      success: 'ワークスペースを作成しました',
      failed: 'ワークスペースの作成に失敗しました',
      disabled: 'このシステムでは招待によるワークスペースへの参加のみが許可されています。自分で作成することはできません。'
    },
    switcher: {
      menuLabel: 'ワークスペースを切り替え',
      currentBadge: '現在',
      homeTooltip: '自分のワークスペース',
      empty: '所属しているワークスペースは1つだけです'
    }
  },
  chat: {
    suggestedQuestions: 'こんな質問ができます',
    refreshSuggestedQuestions: '別の候補',
    replaceDraftTitle: '下書きを置き換えますか？',
    replaceDraftBody: '入力欄のテキストをこのおすすめの質問に置き換えます。',
    historyLoadFailed: '会話履歴を読み込めませんでした。',
    scrollToLatest: '最新のメッセージへ移動',
    thinking: '思考中...',
    thinkingAlt: '思考中',
    preparingAnswer: '回答を準備しています…',
    connectingModelAndGeneratingAnswer: 'モデルに接続して回答を生成しています…',
    modelStillResponding: 'モデルの応答に通常より時間がかかっています。お待ちください…',
    deepThoughtCompleted: '深い思考が完了しました',
    deepThoughtAlt: '深い思考が完了',
    referencesTitle: '関連する内容を{count}件参照',
    referencesDocCount: '{count}件のドキュメントを参照',
    referencesWebCount: '{count}件のWebページを参照',
    referencesDocAndWebCount: '{docCount}件のドキュメントと{webCount}件のWebページを参照',
    referencesDrawerTitle: '出典',
    referencesDrawerTitleWeb: 'Webの出典',
    referencesDrawerTitleDocs: 'ドキュメントの出典',
    referencesDrawerTitleTools: 'ツールの実行結果',
    referencesDrawerTitleMixed: '出典',
    referencesDrawerWebSection: 'Web',
    referencesDrawerDocsSection: 'ドキュメント',
    referencesDrawerToolsSection: 'ツール',
    referencesDrawerEmpty: '出典はありません',
    questionMinimapTitle: 'Q&A',
    questionMinimapPosition: '全 {total} ターン中 {current} ターン目',
    questionMinimapAriaLabel: '質問一覧',
    questionMinimapAttachmentPlaceholder: '（添付ファイル）',
    referenceChunkCount: '{count}件のチャンク',
    fallbackHint: 'ナレッジベースから関連する内容が見つかりませんでした。上記はモデルの直接回答です。',
    truncatedHint: 'モデルの1回あたりの出力上限で回答が途中で打ち切られました。上記は打ち切り前に生成された内容です。',
    requestInfoTitle: 'リクエスト情報',
    requestInfoRequestId: 'Request ID',
    requestInfoMessageId: 'メッセージID',
    requestInfoSessionId: 'セッションID',
    requestInfoUrl: 'リクエスト',
    requestInfoSentAt: '送信日時',
    requestInfoEmpty: 'リクエスト情報はありません',
    channelWeb: 'Web',
    channelApi: 'API',
    channelIm: 'IM',
    chunkLabel: 'チャンク{index}:',
    navigateToDocument: 'ドキュメント詳細を表示',
    referenceSourceBack: 'すべての出典',
    referenceSourceView: '原文を表示',
    referenceSourceRelocate: '再度位置を特定',
    referenceSourceLocating: '引用箇所を特定しています…',
    referenceSourceExact: '原文の該当箇所を特定しました',
    referenceSourcePartial: '確認できた原文を強調表示しています。引用の一部は未照合です',
    referenceSourceBlock: '原文の領域を表示しています。文字の完全一致は未確認です',
    referenceSourceAmbiguous: '一致する箇所が複数あり、特定できません',
    referenceSourceStale: '原文または内容が更新され、引用箇所を特定できません',
    referenceSourcePrevious: '前の引用箇所',
    referenceSourceNext: '次の引用箇所',
    referenceSourceFoundPage: '{page} ページで見つかりました',
    referenceSourceNotFound: '引用箇所を特定できなかったため、原文を開きました',
    referenceSourceOpenWeb: '元の Web ページで該当箇所を開く',
    chunkIdLabel: 'チャンクID:',
    documentIdLabel: 'ドキュメントID:',
    faqIdLabel: 'FAQ ID:',
    faqContainerIdLabel: '所属ドキュメントID:',
    faqAnswersLabel: '回答:',
    chunkOrdinal: 'チャンク{index}',
    previewContent: '内容をプレビュー',
    noPlanSteps: '具体的な手順はありません',
    chunkIndexLabel: 'チャンク#{index}',
    chunkPositionLabel: '（位置: {position}）',
    noRelatedChunks: '関連するチャンクが見つかりません',
    noSearchResults: '検索結果が見つかりません',
    relevanceHigh: '関連性: 高',
    relevanceMedium: '関連性: 中',
    relevanceLow: '関連性: 低',
    relevanceWeak: '関連性: 弱',
    webSearchNoResults: 'Web検索結果が見つかりません',
    otherSource: 'その他の出典',
    webGroupIntro: '以下の{count}件の内容の出典',
    graphConfigTitle: 'グラフ設定',
    entityTypesLabel: 'エンティティタイプ:',
    relationTypesLabel: 'リレーションタイプ:',
    graphResultsHeader: '関連する結果が{count}件見つかりました',
    graphNoResults: '関連するグラフ情報が見つかりません',
    unknownLink: '不明なリンク',
    contentLengthLabel: '長さ{value}',
    notProvided: 'なし',
    errorMessageLabel: 'エラーメッセージ',
    summaryLabel: '要約',
    rawTextLabel: '元テキスト',
    collapseRaw: '原文を折りたたむ',
    expandRaw: '原文を展開',
    noWebContent: 'Webコンテンツを取得できませんでした',
    webFetchStatusSuccess: '取得済み',
    webFetchStatusFailed: '失敗',
    webFetchStatusSkipped: 'スキップ',
    webFetchErrorCode: 'エラーコード',
    webFetchRetryable: '再試行可能',
    webFetchContentRange: '文字範囲 {start}–{end} / 全 {total} 文字',
    webFetchPartialContent: 'ページの一部',
    webFetchSummaryFailed: '要約失敗',
    lengthChars: '{value}文字',
    lengthThousands: '{value}千文字',
    lengthTenThousands: '{value}万文字',
    noDatabaseRecords: '一致するレコードが見つかりません',
    nullValuePlaceholder: '<NULL>',
    chunkCountValue: '{count}件のチャンク',
    documentDescriptionLabel: '説明:',
    documentSourceLabel: '出典:',
    documentFileLabel: 'ファイル:',
    documentMetadataLabel: 'メタデータ',
    documentInfoEmpty: 'ドキュメント情報はありません',
    positionLabel: '位置:',
    chunkPositionValue: 'チャンク#{index}',
    contentLengthLabelSimple: 'コンテンツ長:',
    fullContentLabel: '全文',
    copyContent: '内容をコピー',
    knowledgeBaseCount: '{count}件のナレッジベース',
    noKnowledgeBases: '利用可能なナレッジベースがありません',
    rawOutputLabel: '生の出力',
    wikiWritePageTitle: 'Wikiページの書き込み',
    wikiReplaceTextTitle: 'Wikiテキストの置換',
    wikiRenamePageTitle: 'Wikiページの名前変更',
    wikiDeletePageTitle: 'Wikiページの削除',
    wikiActionCreated: '作成しました',
    wikiActionUpdated: '更新しました',
    wikiActionRenamed: '名前を変更しました',
    wikiActionDeleted: '削除しました',
    wikiFieldSlug: 'スラッグ',
    wikiFieldTitle: 'タイトル',
    wikiFieldPageType: '種類',
    wikiFieldSummary: '要約',
    wikiFieldOldText: '変更前のテキスト',
    wikiFieldNewText: '変更後のテキスト',
    wikiFieldOldSlug: '変更前のスラッグ',
    wikiFieldNewSlug: '変更後のスラッグ',
    wikiFieldAffectedPages: '影響を受けるページ',
    wikiAffectedCount: '{count}件のページリンクを更新しました',
    processError: '処理エラー',
    sessionExcerpt: 'セッション抜粋',
    noAnswerContent: '（回答内容なし）',
    manualSourcesHeading: '参照元',
    noMatchFound: '一致する内容が見つかりません',
    deleteSessionFailed: '削除に失敗しました。しばらくしてから再試行してください！',
    imageTooMany: '画像は最大5枚までです',
    imageTypeSizeError: '10MB以下のJPG/PNG/GIF/WEBPのみ対応しています',
    imageUploadTooltip: '画像をアップロード（貼り付け・ドロップ対応）',
    attachmentUploadTooltip: '添付ファイルをアップロード（ドキュメント、音声など）',
    attachmentWithCount: '{count}件の添付ファイルをアップロードしました',
    attachmentTooMany: '添付ファイルは最大{max}件までです',
    attachmentTotalTooMany: '画像と添付ファイルは合計{max}件までです',
    attachmentTooLarge: 'ファイル{name}が{max}MBの上限を超えています',
    attachmentTypeNotSupported: '未対応のファイル形式です: {name}',
    attachmentUploading: 'アップロード中{progress}%',
    attachmentParsing: '解析中',
    attachmentReady: '解析完了',
    attachmentUploadFailed: '添付ファイルのアップロードに失敗しました',
    attachmentParseFailed: '添付ファイルの解析に失敗しました',
    attachmentStillProcessing: '添付ファイル{name}は解析中です',
    memoryUsedCount: '{count}件のメモリを使用',
    memoryForget: 'このメモリを削除',
    memoryForgotten: 'メモリを削除しました',
    memoryForgetFailed: '削除に失敗しました',
    memoryHint: 'この回答が参照した長期メモリです。削除すると以降は使用されません。',
    backgroundWork: {
      count: '{count} background tasks',
      refresh: 'Refresh',
      structuredResult: 'Structured result',
      updateMessage: 'Additional task instructions',
      sendUpdate: 'Send update',
      stopRequested: 'Cancellation requested',
      actionFailed: 'Action failed. Try again.',
      cancelFailed: 'Cancellation failed. Try again.',
      stop: '停止',
      loading: '出力を読み込んでいます…',
      unavailable: '出力を表示できません',
      states: {
        pending: 'Queued',
        running: 'Running',
        waiting: 'Waiting for input',
        succeeded: 'Completed',
        failed: 'Failed',
        cancelled: 'Cancelled',
        lost: 'Unavailable'
      }
    },
    rewind: {
      tooltip: 'ここに巻き戻す',
      confirmTitle: 'ここに巻き戻しますか？',
      confirmBody: 'これより後の会話を削除します。質問から巻き戻すとその質問自体も消え、入力欄に戻します。チェックポイントがあればワークスペースも戻します。この操作は元に戻せません。',
      confirmButton: '巻き戻す',
      cancelButton: 'キャンセル',
      success: '巻き戻しました',
      reloadFailed: '会話は巻き戻しましたが、履歴を再読み込みできませんでした。古いメッセージが欠けている場合は更新してください',
      failed: '巻き戻しに失敗しました。もう一度お試しください',
      skipped: '会話は巻き戻しましたが、ワークスペースは変更していません',
      skipNoSandbox: '会話は巻き戻しましたが、ワークスペースは変更していません（サンドボックスがありません）',
      skipNoCheckpoint: '会話は巻き戻しましたが、ワークスペースは変更していません（戻せるチェックポイントがありません）'
    },
    sandbox: {
      panelTitle: 'サンドボックス',
      tabArtifacts: 'ファイル',
      tabTerminal: 'ターミナル',
      tabDesktop: 'デスクトップ',
      artifactsEmpty: 'この会話で生成されたファイルはまだありません',
      artifactScope: 'ファイルの範囲',
      artifactsCurrent: 'このターン',
      artifactsAll: 'すべて',
      artifactsSearch: 'ファイル名を検索',
      artifactsNoMatches: '一致するファイルがありません',
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
      paused: 'この会話のサンドボックスは一時停止中です。ターミナルを起動すると再開します。',
      stopped: 'この会話のサンドボックスは実行されていません。停止したか、長時間アイドル状態だったため回収された可能性があります。ターミナルを起動すると再起動します。回収済みの場合は新しいサンドボックスが作成され、以前のファイルやインストールしたソフトウェアは保持されません。',
      start: 'ターミナルを起動',
      connecting: 'サンドボックスに接続中…',
      needsProvision: 'この会話には実行中のサンドボックスがありません。作成すると新しいサンドボックスが起動し、ワークスペースの設定に従って課金されます。',
      createAndStart: '作成して起動',
      noSandbox: 'サンドボックスがまだなく、現在のエージェントにサンドボックスバックエンドが設定されていないため、作成先を決められません。サンドボックスが設定されたエージェントに切り替えるか、コードを実行するメッセージを送信してください。',
      unsupported: '現在のサンドボックスバックエンドは対話型ターミナルに対応していません',
      disconnected: '接続が切断されました',
      retry: '再接続',
      sessionEnded: 'ターミナルセッションが終了しました',
      idleDisconnected: 'アイドル状態のためターミナルが切断されました。サンドボックスは自身のTTLで一時停止します。再接続できます。',
      idleDisconnectedNewShell: 'アイドル状態のためターミナルが切断され、シェルは終了しました（nohup で起動したバックグラウンドジョブは影響を受けません）。再接続すると新しいシェルが開きます。',
      disconnectedNewShell: '接続が切断され、ターミナルのシェルは終了しました（nohup で起動したバックグラウンドジョブは影響を受けません）。再接続すると新しいシェルが開きます。',
      authRevoked: 'ログイン状態が無効になったため、ターミナルが切断されました。再度サインインしてから接続してください。'
    },
    conversationTime: {
      today: '今日{time}',
      yesterday: '昨日{time}',
      thisYear: '{month}/{day} {time}',
      otherYear: '{year}/{month}/{day} {time}'
    }
  },
  knowledgeEditor: {
    titleCreate: 'ナレッジベースを作成',
    titleEdit: 'ナレッジベース設定',
    advanced: {
      title: '詳細設定',
      description: '質問生成やその他の高度な機能を設定します',
      multimodal: {
        label: 'マルチモーダル機能',
        description: '画像などのマルチモーダルコンテンツの理解を有効にします',
        vllmLabel: 'VLLM視覚モデル',
        vllmDescription: 'マルチモーダル理解に必要な視覚言語モデル',
        vllmPlaceholder: 'VLLMモデルを選択（必須）',
        descriptionLanguageLabel: '画像説明の言語',
        descriptionLanguageDescription: '空欄にすると中国語を強制せず、ドキュメントの言語に従います',
        descriptionLanguageAuto: 'ドキュメントの言語に従う',
        customInstructionsLabel: '画像処理の指示',
        customInstructionsDescription: 'OCRとMarkdown出力の仕様は固定したまま、視覚的に優先する対象を追加できます',
        customInstructionsPlaceholder: '例: 銘板、型番、アラームコード、表の単位を優先する…',
        imageVectorLabel: '画像ベクトル検索',
        imageVectorDescription: 'オンにすると、画像の説明を生成した後に埋め込みモデルで画像そのものもエンコードし、説明に書かれていない内容でも画像を検索できるようにします。画像入力に対応した埋め込みモデルが必要で、画像ごとに埋め込み呼び出しが1回増え、ベクトル検索の候補範囲も広がります。以降に取り込み・再解析した文書にのみ適用され、スキャン PDF のページは対象外です',
        imageVectorModelUnsupported: '現在の埋め込みモデルは画像入力を宣言していないため、画像ベクトルは生成も検索もされません',
        imageAttrsSchemaLabel: '観察可能な画像属性',
        imageAttrsSchemaDescription: 'モデルは以下の属性（バックエンドのレジストリで定義）を観察して OCR ポリシーを決めます',
        imagePipelineSectionLabel: '画像解析方式',
        imagePipelineSectionDescription: 'マルチモーダル解析が有効な場合、画像の解析方式を選択できます。',
        imagePipelineLabel: '解析方式',
        advancedSettingsLabel: '詳細設定',
        notesLabel: '補足説明',
        imagePipelinePlaceholder: '解析方式を選択',
        imagePipelineLoading: 'パイプラインを読み込み中…',
        imagePipelineLoadError: 'パイプラインの読み込みに失敗しました',
        imagePipelineValidateError: '現在の設定を検証できませんでした。保存時にバックエンドが再度チェックします。',
        imageAttrsOcrConditions: '観察した属性条件に基づいて OCR を実行',
        imageAttrsOcrConditionsDesc: '観察した属性が以下の条件を満たす場合、その画像に OCR を実行します',
        imagePipelineKbNote: 'デフォルトはナレッジベースの設定に従い、今回のタスク向けに調整できます'
      },
      tableMetadataInstructions: {
        label: 'テーブルメタデータの指示',
        description: 'CSV／Excelの要約に業務コンテキストや項目の意味を追加し、検索精度を高めます',
        placeholder: '例: これは受注テーブルで、金額は人民元、ステータスは社内コードを使用している…'
      },
      autoTag: {
        label: '自動タグ付け',
        description: '解析後、ナレッジベースの既存タグから適切なものを選択します。タグの作成や削除は行いませんが、モデル呼び出しが1回追加で必要になります。',
        modelLabel: '分類モデル',
        modelDescription: '空欄の場合はナレッジベースの要約モデルを使用します。',
        modelPlaceholder: '分類モデルを選択',
        maxTagsLabel: 'ドキュメントあたりの最大タグ数',
        maxTagsDescription: 'ドキュメントごとに既存タグを1〜10件、自動で関連付けます。',
        skipIfTaggedLabel: '既にタグが付いたドキュメントをスキップ',
        skipIfTaggedDescription: '有効にすると、アップロード時に手動でタグ付けしたドキュメントはそのまま維持され、意図した分類が薄まりません。'
      },
      profile: {
        label: 'ナレッジベース説明の自動生成',
        description: 'ドキュメントの追加・削除・要約更新後に、ドキュメントプロファイルの集計から説明を自動生成します。集計自体はモデルを呼び出さず、集計結果が変化したときのみ小さなモデル呼び出しを1回行います。',
        modelLabel: '生成モデル',
        modelDescription: '空欄の場合はナレッジベースの要約モデルを使用します。',
        modelPlaceholder: '生成モデルを選択',
        instructionsLabel: '説明生成の指示',
        instructionsDescription: '対象読者、残すべき用語、文体などを補足します。出力形式は固定のままです。',
        instructionsPlaceholder: '例：サポート担当者向けに、製品ラインを平易に説明し、型番は残す…'
      },
      questionGeneration: {
        modelLabel: '質問生成モデル',
        modelDescription: '未選択の場合はナレッジベースの要約モデルを使用します。',
        modelPlaceholder: '質問生成モデルを選択',
        label: 'AI質問生成',
        description: 'ドキュメント解析時にLLMで各チャンクの関連質問を生成し、検索のリコールを向上させます。有効にするとドキュメントの解析時間が長くなります。',
        countLabel: '質問数',
        countDescription: 'ドキュメントのチャンクごとに生成する質問の数（1〜10）',
        instructionsLabel: '質問生成の指示',
        instructionsDescription: '出力形式はシステム側で固定したまま、対象読者、利用シーン、表現を指定できます',
        instructionsPlaceholder: '例: カスタマーサポートで自然に出てくる質問を生成し、試験問題のような表現は避ける…'
      }
    },
    asr: {
      title: '音声認識',
      description: 'ASR（音声からテキストへの変換）を設定します。有効にすると、音声ファイル（mp3、wav、m4a、flac、oggなど）をアップロードしてテキストに書き起こせます。動画のアップロードには対応していません。',
      label: '音声認識を有効化',
      desc: '有効にすると、ナレッジベースに音声をアップロードでき、音声はテキストに書き起こされて解析と検索に利用されます。',
      modelLabel: 'ASRモデル',
      modelDescription: '音声をテキストに変換するモデル（例: OpenAI Whisper）',
      modelPlaceholder: 'ASRモデルを選択',
      languageLabel: '音声の言語ヒント',
      languageDescription: '任意。主要な言語のヒントを指定すると、一部のASRモデルで精度が向上します。空欄の場合は自動判定します。',
      languagePlaceholder: '例: zh、en。空欄の場合は自動判定'
    },
    multimodal: {
      title: '画像処理の設定',
      description: '画像などの非テキストコンテンツを解析・検索するための画像内容理解を設定します'
    },
    chunking: {
      title: 'チャンク設定',
      description: 'アップロードしたドキュメントを埋め込み前にどう分割するかを制御します。ほとんどの場合はデフォルトのままで問題ありません。検索品質が低い場合のみ調整してください。',
      sizeLabel: 'チャンクサイズ',
      sizeDescription: '1チャンクあたりの最大文字数（100〜4000）。デフォルトの512は英語で約100〜130トークンです。FAQは小さめ（200〜400）、説明文中心のドキュメントは大きめ（1000〜2000）にします。',
      characters: '文字',
      overlapLabel: 'チャンクの重なり',
      overlapDescription: '隣接するチャンク間で共有する文字数（0〜500）。デフォルトの80はサイズの約15%で、現在の研究では最適とされています。FAQや構造化データは0、長文の説明文は150〜200を使用します。',
      separatorsLabel: '区切り文字',
      separatorsDescription: '分割時に優先される文字または文字列です。優先度の高い区切り文字から順に試され、デフォルトの順序は段落 → 文 → 句読点の区切りを優先します。',
      separatorsPlaceholder: '区切り文字を選択またはカスタマイズ',
      parentChildLabel: '親子チャンク分割',
      parentChildDescription: '2階層のチャンク分割です。小さな子チャンクでベクトル一致を行い（高精度なヒット）、LLMには大きな親チャンクを返します（豊富なコンテキスト）。長文ドキュメント（10ページ超）に推奨です。短いFAQではストレージ節約のためオフにするとよいでしょう。',
      parentChunkSizeLabel: '親チャンクのサイズ',
      parentChunkSizeDescription: 'LLMに返すコンテキストチャンクのサイズ（512〜8192）。デフォルトの4096は英語で約1000トークンで、最近のLLMのコンテキストウィンドウに十分収まります。',
      childChunkSizeLabel: '子チャンクのサイズ',
      childChunkSizeDescription: 'ベクトル一致に使う埋め込み対象チャンクのサイズ（64〜2048）。デフォルトの384は約80トークンで、sentence-transformerやBGE系の埋め込みモデルに最適です。',
      strategyLabel: 'チャンク分割戦略',
      strategyDescription: 'ドキュメントをチャンクに分割する方法を選択します。自動モードはドキュメントごとに特性を分析し、最適な戦略を選びます。',
      strategyPlaceholder: 'チャンク分割戦略を選択（空欄の場合は文字数で分割）',
      overlapWarning: 'チャンクサイズに対して重なりが大きすぎます。チャンク同士が内容の大半を共有することになります。',
      advancedLabel: '詳細オプション',
      tokenLimitLabel: 'チャンクあたりのトークン上限',
      tokenLimitDescription: '1チャンクあたりのトークン数の上限（0〜8192）。0で無効（文字数のみで制御）。埋め込みモデルのトークン上限が小さい場合に設定します。MiniLM（256トークン）は200、BGE／Cohere（512トークン）は400が目安です。最近の埋め込みモデル（OpenAI、Voyage、Jina-v3）は2000トークン超に対応しているため、0のままで構いません。',
      languagesLabel: '言語のヒント',
      languagesDescription: 'ヒューリスティックのパターンを指定した言語（DE／EN／ZH）に限定します。空欄の場合はサンプルから自動判定します。単一言語のコーパスでは明示的に指定すると、言語をまたいだ誤検出を防げます。',
      languagesPlaceholder: '自動判定',
      debug: {
        toggle: 'チャンク分割をプレビュー',
        toggleHint: '再アップロードせずに、サンプルテキストでチャンク分割を試せます',
        sampleLabel: 'サンプルテキスト',
        samplePlaceholder: 'Markdownまたはプレーンテキストの断片を貼り付けると、現在の設定でどう分割されるか確認できます…',
        presetLabel: 'サンプルを読み込む:',
        runButton: 'プレビューを実行',
        loading: 'サンプルにチャンク分割を実行中…',
        errorPrefix: 'プレビューに失敗しました',
        selectedTier: '選択された戦略',
        rejected: '不採用の戦略',
        contextHeader: 'コンテキスト見出し',
        fallbackWarning: '戦略チェーンを使い切りました。現在の設定ではこの内容をうまく分割できません',
        stats: {
          chunks: 'チャンク',
          truncated: '省略表示中、合計{total}'
        },
        profile: {
          lines: '行',
          chars: '文字',
          headings: 'Markdown見出し',
          pageBreaks: '改ページ',
          chapterMarkers: '章マーカー',
          languages: '言語'
        },
        samples: {
          markdown: 'Markdownドキュメント',
          faq: 'FAQリスト',
          chapter: 'PDFの章',
          plain: 'プレーンな文章'
        }
      },
      languageOptions: {
        de: 'ドイツ語',
        en: '英語',
        zh: '中国語'
      },
      strategies: {
        legacy: {
          label: '文字数ベース',
          tooltip: '構造を無視し、文字数と区切り文字で再帰的に分割します（従来の動作）。構造ベースの戦略がうまく機能しない内容に使用してください。'
        },
        heuristic: {
          label: '構造ベース',
          tooltip: '改ページ、番号付きセクション、多言語の章マーカー（DE／EN／ZH）、大文字のみのタイトルなど、検出した構造の手がかりで分割します。Markdown見出しのないPDFに最適です。'
        },
        heading: {
          label: '見出しベース',
          tooltip: 'Markdownの見出し境界（#、##、###）で分割し、各チャンクに見出しのパスを保持します。構造の整ったMarkdownに最適です。'
        },
        auto: {
          label: '自動',
          tooltip: 'ドキュメントの特性分析により、アップロードごとに見出しベース・構造ベース・文字数ベースの分割を選び分けます。'
        }
      },
      separators: {
        doubleNewline: '二重改行（\\n\\n）',
        singleNewline: '単一改行（\\n）',
        periodCn: '句点(。)',
        exclamationCn: '感嘆符(！)',
        questionCn: '疑問符(？)',
        semicolonCn: '全角セミコロン(；)',
        semicolonEn: 'セミコロン(;)',
        space: 'スペース( )'
      }
    },
    models: {
      title: 'モデル設定',
      description: 'ナレッジベースに適したAIモデルを選択します',
      llmLabel: 'LLMモデル',
      llmDesc: '要約や概要の生成に使用する大規模言語モデル（任意）',
      llmPlaceholder: 'LLMモデルを選択（任意）',
      embeddingLabel: '埋め込みモデル',
      embeddingDesc: 'テキストのベクトル化に使用する埋め込みモデル',
      embeddingPlaceholder: '埋め込みモデルを選択',
      embeddingLocked: 'ナレッジベースに既にファイルがあるため、埋め込みモデルは変更できません',
      embeddingOptional: '（任意）',
      embeddingWikiOptionalDesc: '任意。設定すると、Wikiのディレクトリ分類における類似度マッチングに使用され、新しいページが既存のフォルダをより適切に再利用できます。未設定の場合はディレクトリツリー全体が使用されます。'
    },
    faqImport: {
      title: 'FAQを一括インポート'
    },
    faq: {
      title: 'FAQ設定',
      description: 'FAQ型ナレッジベースのインデックス戦略とガイダンスを設定します',
      indexModeLabel: 'インデックスモード',
      indexModeDescription: '質問のみをインデックスすると精度が向上し、質問と回答をインデックスするとリコールが向上します。',
      questionIndexModeLabel: '質問のインデックスモード',
      questionIndexModeDescription: '統合: 標準質問と類似質問をまとめてインデックスします。個別: 各質問を独立してインデックスするため検索精度は高まりますが、より多くのストレージが必要です。',
      entryGuide: 'FAQエントリは、標準質問、類似質問、ネガティブ例、複数の回答で構成されます。FAQナレッジベースの詳細画面で管理できます。',
      modes: {
        questionOnly: '質問のみ',
        questionAnswer: '質問＋回答',
        combined: '統合',
        separate: '個別'
      }
    },
    document: {
      title: 'ドキュメント管理'
    },
    messages: {
      loadModelsFailed: 'モデル一覧の読み込みに失敗しました',
      loadDataFailed: 'ナレッジベースのデータの読み込みに失敗しました',
      notFound: 'ナレッジベースが見つかりません',
      nameRequired: 'ナレッジベース名を入力してください',
      summaryRequired: '要約モデルを選択してください',
      multimodalInvalid: 'マルチモーダル設定の検証に失敗しました',
      createSuccess: 'ナレッジベースを作成しました',
      createFailed: 'ナレッジベースの作成に失敗しました',
      missingId: 'ナレッジベースIDがありません',
      buildDataFailed: '送信データの構築に失敗しました',
      updateSuccess: '設定を保存しました',
      indexModeRequired: 'FAQ型ナレッジベースのインデックスモードを選択してください',
      storageChangeConfirm: 'このナレッジベースには既にファイルがあります。ストレージエンジンを変更すると、既存のファイルにアクセスできなくなる可能性があります。続行しますか？'
    },
    share: {
      description: 'ナレッジベースを共有スペースに共有して、メンバーが利用できるようにします',
      hintTitle: '共有に関する注意',
      addShare: '共有',
      unshareConfirm: '「{name}」への共有を解除してもよろしいですか？',
      tip1: '共有すると、共有スペースのメンバーは付与された権限に応じてこのナレッジベースを利用できます',
      tip2: '編集可能権限ではメンバーが内容を変更できます。読み取り専用権限では検索とQ&Aのみ行えます'
    },
    postCreateHint: {
      title: '作成しました',
      footer: '設定の調整を続け、共有やデータソースを設定してから「保存して閉じる」をクリックしてください。',
      followUpDesc: '左側でデータソースを設定するか、共有管理から共有スペースに公開してください'
    },
    footer: {
      instantEffect: 'このページの変更は即時に反映されます。保存は不要です'
    },
    buttons: {
      create: 'ナレッジベースを作成',
      saveAndClose: '保存して閉じる'
    },
    wikiBrowser: {
      viewInGraph: 'グラフで表示',
      filterSummary: '要約',
      filterEntity: 'エンティティ',
      filterConcept: '概念',
      filterSynthesis: '総合',
      filterComparison: '比較',
      version: 'v{ver}',
      gallery: {
        attr: {
          builtin_caption: '説明',
          builtin_caption_description: 'モデルが生成した画像の説明',
          builtin_ocr_text: 'OCR テキスト',
          builtin_ocr_text_description: 'OCR で画像から抽出した文字',
          builtin_page: '文書のページ',
          builtin_page_description: '元の文書ごとに PDF のページ順で表示します。ページ不明の画像は各文書の末尾に表示します。',
          builtin_created_at: '作成日時',
          builtin_created_at_description: '所属ドキュメントチャンクの作成日時',
          builtin_updated_at: '更新日時',
          builtin_updated_at_description: '所属ドキュメントチャンクの最終更新日時',
          builtin_is_enabled: '有効状態',
          builtin_is_enabled_description: '所属ドキュメントチャンクが検索対象かどうか',
          builtin_is_enabled_value_true: '有効',
          builtin_is_enabled_value_false: '無効'
        }
      }
    },
    indexing: {
      title: 'インデックス戦略',
      description: 'ドキュメント処理のパイプラインを設定します。各インデックス方式は個別に有効化・無効化できます。',
      searchTitle: 'RAG検索',
      searchDesc: 'ドキュメントをチャンク化し、ベクトル化とキーワードインデックスを作成してハイブリッド検索を行います',
      wikiTitle: 'Wikiナレッジベース',
      wikiDesc: '相互リンクされたWikiページを自動生成し、構造化されたナレッジ体系を構築します',
      atLeastOne: 'インデックス戦略を1つ以上有効にしてください',
      embeddingRequired: 'RAG検索には埋め込みモデルが必要です',
      lockedTip: 'ナレッジベースに内容がある間はインデックス戦略を変更できません。先にナレッジベースを空にしてください。',
      rebuildConfirmTitle: 'インデックスを再構築',
      rebuildConfirmBody: 'インデックス戦略が変更されました。既存の{count}件のドキュメントを再処理しますか？時間がかかる場合があります。',
      rebuildSuccess: '{count}件のドキュメントの再構築タスクを登録しました',
      rebuildSkip: '再構築は後からデータソース画面で手動で実行できます'
    },
    wiki: {
      title: 'Wiki設定',
      synthesisModelLabel: 'Wiki生成モデル',
      synthesisModelPlaceholder: 'Wiki生成に使用するLLMモデルを選択',
      synthesisModelTip: '未設定の場合は要約モデルが使用されます',
      autoGenerateLabel: 'Wikiページを自動生成',
      autoGenerateTip: '無効にしてもWikiページの閲覧と手動編集は利用できますが、ドキュメント処理でLLMによるページの生成や更新は行われません',
      extractionGranularityLabel: '抽出の粒度',
      contentInstructionsLabel: 'Wiki本文の生成指示',
      contentInstructionsTip: '要約・ページ・インデックスの重点やトーンを制御します。引用、統合、事実性のルールはシステム側で固定されます。変更を反映するには既存コンテンツを再処理してください。',
      contentInstructionsPlaceholder: '例: 法務レビューのトーンで、担当者・期限・リスクを重視する…',
      extractionInstructionsLabel: 'Wiki抽出の重点',
      extractionInstructionsTip: 'システムのJSONおよび引用プロトコルは変更せずに、優先して抽出するドメイン固有のエンティティや概念を記述します。',
      extractionInstructionsPlaceholder: '例: 製品、バージョン、組織、担当者、中核となる技術概念を優先する…',
      extractionGranularityTip: 'ドキュメントごとに抽出するWikiのエンティティ／概念の数を制御します。細かいほどインデックスは絞り込まれ、粗いほど網羅的になります',
      granularityFocused: '重点',
      granularityStandard: '標準',
      granularityExhaustive: '網羅',
      granularityFocusedHint: 'ドキュメントの主題のみを抽出します（例: 履歴書なら本人とそのプロジェクト）。最もすっきりしますが、副次的なエンティティを取りこぼす場合があります。',
      granularityStandardHint: '主題に加えて、十分に言及されている副次的なエンティティや概念も抽出します。名前だけの言及は除外します。推奨のデフォルトです。',
      granularityExhaustiveHint: '技術スタックやツールへの軽微な言及も含め、名前付きのエンティティと概念をすべて抽出します。ナレッジベースを用語集として使う場合に適しています。'
    },
    basic: {
      title: '基本情報',
      description: 'ナレッジベースの名前と説明を設定します',
      kbId: 'ナレッジベースID',
      kbIdDesc: 'API連携でナレッジベースを指定する際にこのIDを使用します',
      typeLabel: 'ナレッジベースの種類',
      typeDocument: 'ドキュメント型',
      typeFAQ: 'FAQ型',
      typeDescription: 'FAQ型は構造化されたQ&Aデータに適しています。ドキュメント型はファイルの解析とチャンク分割に対応します。Wiki型はLLMで相互リンクされたナレッジページを自動構築します。',
      nameLabel: 'ナレッジベース名',
      namePlaceholder: 'ナレッジベース名を入力してください',
      descriptionLabel: 'ナレッジベースの説明',
      descriptionPlaceholder: 'ナレッジベースの説明を入力してください（任意）',
      profile: {
        title: 'AI 生成の説明',
        hint: 'ドキュメントプロファイルの集計から生成されます。上の手入力の説明を上書きすることはなく、エージェントは両方を読んで質問がこのナレッジベースに属するか判断します。',
        empty: 'まだ生成されていません。ドキュメントをアップロードし要約が完了したら、下のボタンで生成してください。',
        noDocuments: 'このナレッジベースには解析済みのドキュメントがまだありません。',
        questions: '典型的な質問',
        generate: 'AI 説明を生成',
        regenerate: '再生成',
        adopt: '説明として使用',
        generated: 'AI 説明を生成しました',
        generateFailed: 'AI 説明の生成に失敗しました',
        adopted: '説明欄にコピーしました。保存すると反映されます',
        failed: '前回の生成に失敗しました：{error}',
        generatedAt: '{time} に生成 · {count} 件のドキュメントに基づく'
      }
    },
    errors: {
      vectorStoreBindingInvalid: '選択したベクトルストアは使用できません。別のストアを選択するか、システムのデフォルトを使用してください。',
      vectorStoreUnavailable: '選択したベクトルストアは現在利用できません。設定 → ベクトルストアで接続設定を確認してください。'
    },
    sidebar: {
      basic: '基本情報',
      models: 'モデル設定',
      vectorStore: 'ベクトルストア',
      chunking: 'チャンク設定',
      storage: 'ストレージエンジン',
      advanced: '詳細設定',
      faq: 'FAQ設定',
      graph: 'ナレッジグラフ',
      multimodal: '画像処理',
      asr: '音声',
      datasource: 'データソース',
      share: '共有',
      activity: 'アクティビティ'
    },
    navGroups: {
      basic: '基本',
      processing: 'インデックスと解析',
      data: 'ストレージとデータ',
      integration: '公開',
      management: '管理と監査'
    },
    activity: {
      title: 'アクティビティ',
      description: 'このナレッジベースの重要な変更履歴と、バックグラウンドタスクへの導線を表示します。保持期間は監査ログのポリシーに従います。',
      allOutcomes: 'すべての結果',
      allActions: 'すべての操作',
      refresh: '更新',
      retry: '再試行',
      empty: 'アクティビティはまだありません',
      emptyFiltered: '条件に一致するアクティビティ記録がありません',
      clearFilters: 'フィルタをクリア',
      loadingMore: '読み込み中…',
      end: 'これ以前のアクティビティはありません',
      loadFailed: 'アクティビティの読み込みに失敗しました',
      systemActor: 'システム',
      actorWithAPIKey: '{actor} · API Key · {name}',
      actorAPIKey: 'API Key · {name}',
      viaAssistant: 'Xiaozhi アシスタント経由',
      knowledgeBase: 'ナレッジベース',
      countItems: '{count}件',
      titleWithCount: '{title}ほか{count}件',
      importSummary: '成功{success} / 失敗{failed} / スキップ{skipped}',
      detailValues: {
        user: 'ユーザ操作',
        manual: '手動',
        schedule: 'スケジュール',
        system: 'システム',
        pending: '保留中',
        completed: '完了',
        partial: '一部完了',
        canceled: 'キャンセル',
        failed: '失敗',
        enqueue: 'タスク登録',
        reuse_vectors: 'ベクトルを再利用',
        reparse: '再解析',
        viewer: '読み取り専用',
        editor: '編集可能',
        admin: '管理',
        append: '追加',
        replace: '上書き'
      },
      outcomes: {
        accepted: '受付済み',
        success: '成功',
        failed: '失敗',
        partial: '一部成功',
        canceled: 'キャンセル',
        denied: '拒否'
      },
      actions: {
        'kb.created': 'ナレッジベースを作成',
        'kb.updated': 'ナレッジベースを更新',
        'kb.deleted': 'ナレッジベースを削除',
        'kb.duplicated': 'ナレッジベースを複製',
        'kb.clone_started': '複製を開始',
        'kb.clone_completed': '複製が完了',
        'kb.clone_failed': '複製に失敗',
        'knowledge.created': 'ナレッジを追加',
        'knowledge.updated': 'ナレッジを更新',
        'knowledge.deleted': 'ナレッジを削除',
        'knowledge.batch_deleted': 'ナレッジを一括削除',
        'knowledge.reparse_started': '再解析を開始',
        'knowledge.parse_canceled': '解析をキャンセル',
        'knowledge.move_started': 'ナレッジの移動を開始',
        'knowledge.move_completed': 'ナレッジの移動が完了',
        'knowledge.move_failed': 'ナレッジの移動に失敗',
        'tag.created': 'タグを作成',
        'tag.updated': 'タグを更新',
        'tag.deleted': 'タグを削除',
        'datasource.created': 'データソースを作成',
        'datasource.updated': 'データソースを更新',
        'datasource.deleted': 'データソースを削除',
        'datasource.sync_started': 'データソースの同期を開始',
        'datasource.sync_completed': 'データソースの同期が完了',
        'datasource.sync_failed': 'データソースの同期に失敗',
        'datasource.paused': 'データソースを一時停止',
        'datasource.resumed': 'データソースを再開',
        'kb.share_added': '共有を追加',
        'kb.share_permission_changed': '共有権限を変更',
        'kb.share_removed': '共有を解除',
        'wiki.content_changed': 'Wikiの内容を変更',
        'faq.import_started': 'FAQのインポートを開始',
        'faq.import_completed': 'FAQのインポートが完了',
        'faq.import_failed': 'FAQのインポートに失敗'
      },
      detailFields: {
        task_id: 'タスクID',
        trigger: 'トリガ',
        processing_status: '処理ステータス',
        source_kb_id: '移動元ナレッジベースID',
        target_kb_id: '移動先ナレッジベースID',
        sync_log_id: '同期ログID',
        mode: 'モード',
        attempt: '処理試行回数',
        count: '件数',
        total: '合計',
        processed: '処理済み',
        failed: '失敗',
        skipped: 'スキップ',
        failure_stage: '失敗した段階'
      },
      targets: {
        knowledge_base: 'ナレッジベース',
        knowledge: 'ナレッジ',
        faq_entry: 'FAQエントリ',
        knowledge_tag: 'タグ',
        data_source: 'データソース',
        knowledge_base_share: '共有',
        knowledge_move: 'ナレッジの移動',
        wiki: 'Wiki'
      },
      drawer: {
        sectionSummary: '概要',
        sectionIdentifiers: '識別子',
        sectionTask: 'タスク情報',
        targetChange: '変更内容'
      },
      expanded: {
        targetType: '対象の種類',
        targetId: '対象ID',
        actorId: '実行者ID',
        apiKeyName: 'APIキー名',
        apiKeyId: 'APIキーID',
        agentSessionId: 'アシスタント会話 ID',
        agentOperation: 'アシスタントの操作',
        details: '詳細'
      },
      columns: {
        time: '日時',
        action: '操作',
        target: '対象',
        actor: '実行者',
        outcome: '結果'
      }
    }
  },
  embedPublish: {
    copyCode: 'コードをコピー'
  },
  knowledgeList: {
    detail: {
      title: '共有ナレッジベース',
      sourceOrg: '共有スペース',
      myPermission: '自分の権限'
    },
    sections: {
      tenantOthers: 'ワークスペース・他のメンバー',
      tenantReadonly: 'ワークスペース・閲覧のみ'
    },
    empty: {
      title: 'ナレッジベースがまだありません'
    }
  },
  createChat: {
    title: 'こんにちは、Xiaozhiです。あなたのナレッジを、すぐそばに',
    newSessionTitle: '新しいセッション',
    openProject: 'プロジェクトを選択',
    clearProject: '解除',
    pickFailed: '選択したパスを開けませんでした',
    messages: {
      createFailed: 'セッションの作成に失敗しました',
      createError: 'セッションの作成に失敗しました。しばらくしてから再試行してください'
    }
  },
  input: {
    addModel: 'モデルを追加',
    placeholder: '質問や依頼内容を入力…',
    agentMode: 'スマート推論',
    normalMode: 'クイック回答',
    normalModeDesc: 'ナレッジベースに基づくRAG Q&A',
    agentModeDesc: '多段階の思考による深い分析',
    agentMissingAllowedTools: '許可するツール',
    agentMissingSummaryModel: 'チャットモデル',
    agentMissingRerankModel: 'リランクモデル',
    customAgentMissingSummaryModel: 'チャットモデル',
    customAgentMissingRerankModel: 'リランクモデル',
    goToAgentEditor: '設定に移動 →',
    agentNotReadyDetail: 'エージェント「{agentName}」は準備できていません。次の項目を設定してください: {reasons}',
    sharedAgentNotReadyDetail: '共有エージェント「{agentName}」は準備できていません（不足: {reasons}）。共有元スペースの管理者に設定の完了を依頼してください。',
    knowledgeBase: 'ナレッジベース',
    knowledgeBaseWithCount: 'ナレッジベース（{count}）',
    notConfigured: '未設定',
    sharedAgentModelLabel: '共有エージェントのモデル',
    noModel: '利用可能なモデルがありません',
    modelAuto: '既定',
    modelFollowDefault: '既定に従う',
    modelAutoHint: '現在のナレッジベースのチャットモデル。ナレッジベース外や未設定の場合は、最初に利用可能なチャットモデルを使用します',
    stopGeneration: '生成を停止',
    send: '送信',
    steerRetry: '再送信',
    webSearchDisabledByAgent: '現在のエージェントによりWeb検索が無効になっています',
    kbLockedByAgent: '現在のエージェントによりナレッジベース設定がロックされています',
    kbDisabledByAgent: '現在のエージェントによりナレッジベースが無効になっています',
    modelLockedByAgent: '現在のエージェントによりモデル選択がロックされています',
    imageUploadDisabledByAgent: 'このエージェントでは画像アップロードが有効になっていません',
    voiceTooltip: '押したまま話す（{shortcut}）',
    voicePreparing: 'マイクを準備しています。ボタンが赤くなってから話してください',
    voiceRecording: '録音中、離すと終了します',
    voiceReleasedEarly: 'マイクの準備ができていません。ボタンが赤くなるまで押したまま話してください',
    voiceTranscribing: '音声を認識しています…',
    voiceUnsupported: 'このブラウザは録音に対応していません',
    voiceInsecureContext: '音声入力には HTTPS または localhost でのアクセスが必要です',
    voicePermissionDenied: 'マイクを使用できません。ブラウザでマイクの使用を許可してください',
    voiceDeviceError: '利用可能なマイクが見つかりません',
    voiceDecodeError: '録音の処理に失敗しました。もう一度お試しください',
    voiceTranscribeFailed: '音声認識に失敗しました。エージェントの ASR モデル設定を確認してください',
    voiceEmptyResult: '音声が認識されませんでした',
    goToAgentSettings: 'エージェント設定に移動',
    hostApprovalMode: {
      ask: '承認を求める',
      askHint: '削除とワークスペース外への書き込みは確認します',
      auto: '代わりに承認',
      autoHint: 'モデルが代わりに判断し、中断しません',
      switchFailed: '承認モードを切り替えられませんでした'
    },
    messages: {
      enterContent: '先に内容を入力してください。',
      replying: '回答中です。しばらくしてから再試行してください。',
      steerFailed: 'メッセージの追加に失敗しました。再試行してください。',
      agentSwitchedOn: 'スマート推論に切り替えました',
      agentSwitchedOff: 'クイック回答に切り替えました',
      agentSelected: 'エージェント「{name}」を選択しました',
      webSearchNotConfigured: 'Web検索エンジンが未設定です。設定でプロバイダと認証情報を設定してください。',
      webSearchEnabled: 'Web検索を有効にしました',
      webSearchDisabled: 'Web検索を無効にしました',
      sessionMissing: 'セッションIDが存在しません',
      messageMissing: 'メッセージIDを取得できません。ページを更新して再試行してください。',
      stopSuccess: '生成を停止しました',
      stopFailed: '停止に失敗しました。再試行してください。'
    },
    webSearch: {
      toggleOn: 'Web検索を有効化',
      toggleOff: 'Web検索を無効化',
      notConfigured: 'Web検索エンジンが未設定です'
    }
  },
  manualEditor: {
    defaultTitlePrefix: '新規ドキュメント',
    noDocumentKnowledgeBases: '利用可能なドキュメント型ナレッジベースがありません。先に作成してください',
    actions: {
      cancel: 'キャンセル',
      saveDraft: '下書きを保存',
      publish: '公開'
    },
    loading: {
      content: '内容を読み込み中...',
      preparing: 'エディタを準備中...'
    },
    status: {
      draftTag: 'ステータス: 下書き',
      publishedTag: 'ステータス: 公開済み',
      lastUpdated: '最終更新: {time}',
      counter: '{chars} 文字 · {lines} 行'
    },
    form: {
      knowledgeBasePlaceholder: 'ナレッジベースを選択',
      titleLabel: 'ナレッジのタイトル',
      knowledgeBaseLabel: '対象のナレッジベース',
      titlePlaceholder: 'タイトルを入力',
      contentPlaceholder: 'Markdownに対応しています。#見出し、リスト、コードブロックなどが使えます。'
    },
    success: {
      draftSaved: '下書きを保存しました',
      published: 'ナレッジを公開し、インデックス作成を開始しました'
    },
    warning: {
      selectKnowledgeBase: '対象のナレッジベースを選択してください',
      enterTitle: 'ナレッジのタイトルを入力してください',
      enterContent: 'ナレッジの内容を入力してください',
      contentTooShort: '内容が短すぎます。公開する前に情報を追加してください'
    },
    error: {
      fetchDetailFailed: 'ナレッジ詳細の取得に失敗しました',
      saveFailed: '保存に失敗しました。しばらくしてから再試行してください'
    },
    labels: {
      currentKnowledgeBase: '現在のナレッジベース'
    },
    section: {
      content: '内容'
    },
    title: {
      edit: 'Markdownナレッジを編集',
      create: 'Markdownナレッジを作成'
    },
    preview: {
      empty: 'まだ内容がありません'
    },
    view: {
      edit: '編集',
      split: '分割',
      preview: 'プレビュー',
      splitUnavailable: '幅が足りません。ドロワーを広げるか全画面にすると分割できます',
      groupLabel: 'エディタ表示'
    },
    shortcuts: {
      title: 'ショートカット',
      continueList: 'リストを続ける',
      indent: 'インデント / Shift+Tab で解除'
    },
    toolbar: {
      bold: '太字',
      italic: '斜体',
      strike: '取り消し線',
      inlineCode: 'インラインコード',
      heading1: '見出し1',
      heading2: '見出し2',
      heading3: '見出し3',
      bulletList: '箇条書きリスト',
      orderedList: '番号付きリスト',
      taskList: 'タスクリスト',
      blockquote: '引用',
      codeBlock: 'コードブロック',
      link: 'リンクを挿入',
      image: '画像を挿入',
      table: '表を挿入',
      horizontalRule: '水平線',
      headingGroup: '見出し',
      insertGroup: '挿入'
    },
    table: {
      column1: '列1',
      column2: '列2',
      cell: '内容'
    },
    placeholders: {
      heading: '見出し{level}',
      listItem: 'リスト項目',
      taskItem: 'タスク項目',
      quote: '引用テキスト',
      code: 'コード内容',
      linkText: 'リンクテキスト',
      imageAlt: '説明',
      bold: '太字テキスト',
      italic: '斜体テキスト',
      strike: '取り消し線',
      inlineCode: 'コード'
    },
    assistant: {
      button: 'アシスタント',
      tooltip: 'アシスタントに書いてもらう',
      continue: '続きを書く',
      outline: 'アウトラインを作成',
      polish: '全文を推敲',
      summarize: '要点をまとめる',
      open: 'アシスタントを開く',
      prompts: {
        continue: '本文の末尾から、前の内容に続く段落を一つ書き足してください。',
        outline: 'タイトルと現在の内容をもとに、この文書の構成がわかるアウトラインを作り、本文の先頭に書いてください。',
        polish: '本文を推敲してください。誤字や不自然な文を直し、意味は変えずに段落ごとに修正してください。',
        summarize: 'この文書の要点をチャットでまとめてください。本文は変更しないでください。'
      }
    }
  },
  file: {
    upload: 'ファイルをアップロード'
  },
  mentionDetail: {
    readOnlyFromAgent: 'この会話内でのみ読み取り専用。ナレッジベース一覧には表示されません',
    faqCount: 'Q&A{count}件',
    kbCount: 'ドキュメント{count}件',
    mcpToolCount: 'ツール{count}件',
    mcpNotSynced: 'ツール未同期',
    mcpStale: '再同期が必要',
    belongsToKb: 'ナレッジベース: ',
    belongsToOrg: '共有スペース: ',
    noCompatibleKbForAgent: 'このエージェントのツールはスコープ内のナレッジベースの機能と一致しないため、参照できるナレッジベースがありません。',
    tag: 'タグ',
    searchPlaceholder: 'ナレッジ・ファイル等を検索',
    searchInGroup: '{group}内を検索…',
    typeToSearch: '{\'@\'} の後に入力して検索…',
    viewAll: 'すべて表示',
    back: '戻る'
  },
  mentionBrowser: {
    browse: 'フォルダーで参照',
    path: 'フォルダーパス',
    root: 'ルート',
    searchFolder: 'このフォルダーを検索',
    searchKb: 'ナレッジベースを検索',
    subtree: 'サブフォルダーも検索します。',
    wholeKb: 'ナレッジベース全体が選択されています。ファイルの選択で範囲は狭まりません。',
    tags: '既存のタグで選択したファイルが絞り込まれます。',
    folderCount: 'サブフォルダーを含め {count} 件',
    selected: '選択済み',
    deleting: '削除中',
    unsupported: 'このエージェントでは未対応の形式',
    forbidden: 'この内容へのアクセス権がありません。',
    missing: 'フォルダーが無効です。戻って選択し直してください。',
    error: '読み込みに失敗しました。再試行してください。',
    retry: '再試行',
    empty: 'この表示にファイルはありません。',
    previous: '前へ',
    next: '次へ',
    page: '{page} ページ · {total} 件'
  },
  common: {
    confirm: '確認',
    cancel: 'キャンセル',
    fullscreen: '全画面',
    exitFullscreen: '全画面を終了',
    save: '保存',
    delete: '削除',
    edit: '編集',
    copy: 'コピー',
    copied: 'コピーしました',
    copySuccess: 'コピーしました',
    loading: '読み込み中...',
    noMoreData: 'すべての内容を読み込みました',
    loadMore: 'さらに読み込む',
    error: 'エラー',
    success: '成功',
    failed: '失敗',
    selectAll: 'すべて選択',
    yes: 'はい',
    no: 'いいえ',
    close: '閉じる',
    back: '戻る',
    next: '次へ',
    finish: '完了',
    all: 'すべて',
    clear: 'クリア',
    on: 'オン',
    off: 'オフ',
    confirmDelete: '削除の確認',
    deleteFailed: '削除に失敗しました',
    operationFailed: '操作に失敗しました',
    file: 'ファイル',
    skill: 'スキル',
    knowledgeBase: 'ナレッジベース',
    noResult: '結果がありません',
    remove: '削除',
    avatar: 'アバター',
    defaultUser: 'ユーザ',
    copyFailed: 'コピーに失敗しました',
    retry: '再試行',
    expand: '展開',
    unsavedChanges: {
      title: '未保存の変更があります',
      body: '閉じると現在の変更は失われます。閉じますか？',
      discard: '変更を破棄',
      keepEditing: '編集を続ける'
    }
  },
  authStore: {
    errors: {
      parseUserFailed: 'ユーザ情報の解析に失敗しました',
      parseTenantFailed: 'ワークスペース情報の解析に失敗しました',
      parseKnowledgeBasesFailed: 'ナレッジベース一覧の解析に失敗しました',
      parseCurrentKnowledgeBaseFailed: '現在のナレッジベースの解析に失敗しました'
    }
  },
  auth: {
    account: 'アカウント',
    accountPlaceholder: 'アカウントを入力',
    accountRequired: 'アカウントを入力してください',
    accountDescription: 'プラットフォームへのログイン用アカウント',
    login: 'ログイン',
    logout: 'ログアウト',
    oidcLogin: 'OIDCでログイン',
    oidcLoginWithProvider: '{provider}でログイン',
    redirectingToOIDC: 'IDプロバイダにリダイレクトしています...',
    orContinueWith: 'または次の方法で続行',
    oidcLoginFailed: 'OIDCログインに失敗しました',
    username: 'ユーザ名',
    email: 'メールアドレス',
    password: 'パスワード',
    confirmPassword: 'パスワードの確認',
    loginSuccessTitle: 'ログインしました',
    loginSuccessContent: 'おかえりなさい。{name}にログインしました',
    loggingIn: 'ログイン中...',
    register: '登録',
    registering: '登録中...',
    createAccount: 'アカウントを作成',
    haveAccount: 'すでにアカウントをお持ちですか？',
    backToLogin: 'ログインに戻る',
    loginHint: 'ログインして続行してください。初めての方は下からアカウントを作成できます。',
    firstTime: '初めてご利用ですか？',
    registerSuccess: '登録が完了しました。ログインしてください',
    registerFailed: '登録に失敗しました',
    registerSubtitle: 'アカウントを作成して利用を始めましょう',
    emailPlaceholder: 'メールアドレスを入力',
    passwordPlaceholder: 'パスワードを入力',
    confirmPasswordPlaceholder: 'パスワードを再入力',
    usernamePlaceholder: 'ユーザ名を入力',
    emailRequired: 'メールアドレスを入力してください',
    emailInvalid: '正しいメールアドレスの形式で入力してください',
    passwordRequired: 'パスワードを入力してください',
    passwordMinLength: 'パスワードは8文字以上で入力してください',
    passwordMaxLength: 'パスワードは1024文字以内で入力してください',
    passwordMustContainLetter: 'パスワードには英字を含めてください',
    passwordMustContainLowercaseLetter: 'パスワードには英小文字を含めてください',
    passwordMustContainUppercaseLetter: 'パスワードには英大文字を含めてください',
    passwordMustContainNumber: 'パスワードには数字を含めてください',
    passwordMustContainSpecialChar: 'パスワードには特殊文字を含めてください: {specialChars}',
    usernameRequired: 'ユーザ名を入力してください',
    usernameMinLength: 'ユーザ名は2文字以上で入力してください',
    usernameMaxLength: 'ユーザ名は20文字以内で入力してください',
    usernameInvalid: 'ユーザ名に使用できるのは英数字、アンダースコア、漢字のみです',
    confirmPasswordRequired: 'パスワードを再入力してください',
    passwordMismatch: '入力したパスワードが一致しません',
    loginError: 'アカウントまたはパスワードを確認してください',
    loginErrorRetry: 'ログインに失敗しました。しばらくしてから再試行してください',
    registerError: '登録に失敗しました。しばらくしてから再試行してください',
    workspaceOnboarding: {
      title: 'ワークスペースを選択',
      description: '続行するには個人スペースを作成してください。',
      create: 'ワークスペースを作成',
      invitations: '招待を表示',
      loadingPolicy: '利用できるワークスペースの選択肢を確認中…',
      policyLoadFailed: 'ワークスペースの権限を読み込めませんでした。接続を確認して再試行してください。',
      retry: '再読み込み',
      inviteOnlyTitle: 'ワークスペースへの招待待ち',
      inviteOnlyDescription: '個人ワークスペースの作成は無効になっています。ワークスペース管理者からの招待を確認して承諾してください。',
      inviteOnlyNotice: 'このアカウントは招待によってのみ既存のワークスペースに参加できます',
      help: '今すぐワークスペースを作成することも、後で戻って招待を承諾することもできます。',
      inviteOnlyHelp: 'まだ招待がありませんか？登録したメールアドレスをワークスペース管理者に伝えて、招待を依頼してください。'
    }
  },
  inviteRegister: {
    bannerTitle: '「{tenant}」への参加に招待されています',
    bannerHint: '以下の項目を入力して登録してください。登録が完了すると自動的にチームに参加します。',
    bannerHintLogin: 'ログインすると、このチームに自動的に参加します。',
    loading: '招待リンクを確認中…',
    invalidTitle: '招待リンクが無効か、取り消されています',
    invalidBody: '招待した方に新しいリンクの送付を依頼するか、既存のアカウントでログインしてください。',
    backToLogin: 'ログインに戻る',
    title: '登録を完了',
    subtitle: '「{tenant}」への参加に招待されています',
    email: 'メールアドレス',
    emailPlaceholder: 'your{\'@\'}example.com',
    emailHint: '自分が使用できるメールアドレスを入力してください。',
    emailInvalid: '有効なメールアドレスを入力してください',
    username: '表示名',
    usernamePlaceholder: '表示名を入力',
    password: 'パスワードを設定',
    passwordPlaceholder: '6文字以上',
    confirmPassword: 'パスワードの確認',
    submit: '登録を完了',
    submitting: '送信中…',
    success: '登録が完了しました。ワークスペースに移動します…',
    joined: 'チームに参加しました。',
    failed: '登録に失敗しました。しばらくしてから再試行してください',
    usernameRequired: '表示名は必須です',
    passwordTooShort: 'パスワードは6文字以上で入力してください',
    passwordMismatch: 'パスワードが一致しません'
  },
  initialization: {
    skip: 'スキップ',
    next: '次へ'
  },
  graphSettings: {
    title: 'ナレッジグラフの設定',
    description: 'エンティティとリレーションの抽出を設定し、テキストからナレッジグラフを自動的に構築します（注: Wiki内の「ページリンクグラフ」とは別のものです。あちらはWikiページ間の参照関係を示し、こちらはLLMが抽出したエンティティとリレーションのグラフです）',
    enableLabel: 'エンティティとリレーションの抽出を有効化',
    enableDescription: '有効にすると、テキストからエンティティとリレーションを自動的に抽出します',
    tagsLabel: 'リレーションの種類',
    tagsDescription: '抽出するリレーションの種類のタグをカンマ区切りで定義します',
    tagsPlaceholder: 'リレーションの種類を入力（例: works_at, colleague, friend）',
    generateRandomTags: 'タグをランダム生成',
    sampleTextLabel: 'サンプルテキスト',
    sampleTextDescription: 'エンティティとリレーションの抽出をテストするためのサンプルテキスト',
    sampleTextPlaceholder: 'エンティティとリレーションを含むテキストを入力...',
    customInstructionsLabel: '抽出の追加指示',
    customInstructionsDescription: '構造化出力の形式は維持したまま、対象分野の範囲、エンティティの絞り込み、属性の指針などを追加できます',
    customInstructionsPlaceholder: '例: 契約当事者、金額、履行期日、責任に注目する…',
    generateRandomText: 'テキストをランダム生成',
    entityListLabel: 'エンティティ一覧',
    entityListDescription: 'テキストから抽出されたエンティティとその属性',
    nodeNamePlaceholder: 'エンティティ名を入力',
    attributePlaceholder: '属性値を入力',
    addAttribute: '属性を追加',
    manageEntitiesLabel: 'エンティティの管理',
    manageEntitiesDescription: 'エンティティノードを追加・削除します',
    addEntity: 'エンティティを追加',
    relationListLabel: 'リレーション一覧',
    relationListDescription: 'エンティティ間のリレーションを定義します',
    selectEntity: 'エンティティを選択',
    selectRelationType: 'リレーションの種類を選択',
    manageRelationsLabel: 'リレーションの管理',
    manageRelationsDescription: 'エンティティ間のリレーションを追加・削除します',
    addRelation: 'リレーションを追加',
    extractActionsLabel: '抽出の操作',
    extractActionsDescription: 'エンティティとリレーションの抽出を実行したり、サンプルデータを管理したりします',
    startExtraction: '抽出を開始',
    extracting: '抽出中...',
    defaultExample: 'デフォルトの例',
    clearExample: '例をクリア',
    completeModelConfig: '先にモデルの設定を完了してください',
    tagsGenerated: 'タグを生成しました',
    tagsGenerateFailed: 'タグの生成に失敗しました',
    textGenerated: 'テキストを生成しました',
    textGenerateFailed: 'テキストの生成に失敗しました',
    pleaseInputText: '先にサンプルテキストを入力してください',
    extractSuccess: 'エンティティとリレーションを抽出しました',
    extractFailed: 'エンティティとリレーションの抽出に失敗しました',
    exampleLoaded: '例を読み込みました',
    exampleCleared: '例をクリアしました',
    checkingAvailability: 'ナレッジグラフの利用状況を確認中…',
    checkAvailabilityFailed: 'ナレッジグラフの利用状況を確認できませんでした。再試行してください。',
    disabledWarning: 'ナレッジグラフのデータベースが有効になっていないため、エンティティとリレーションの抽出は利用できません',
    howToEnable: 'ナレッジグラフを有効にするには？'
  },
  retrievalSettings: {
    title: '検索設定',
    description: 'ナレッジベース検索とメッセージ検索に共通する検索パラメータを設定します。値は ContextDB 公式検索 API にそのまま渡されます',
    topKLabel: '検索返回数 (Top K)',
    topKDescription: '1 回の検索で返すフラグメント数、範囲 1–10。ContextDB 公式の既定値は 5',
    similarityThresholdLabel: '類似度のしきい値',
    similarityThresholdDescription: 'この関連性を下回るフラグメントは除外されます。範囲 0–1。ContextDB 公式の既定値は 0.6',
    vectorWeightLabel: 'ベクトル重み',
    vectorWeightDescription: 'ベクトル検索とキーワード検索のバランス。範囲 0–1。ContextDB 公式の既定値は 0.7',
    queryRewriteLabel: 'クエリの書き換え',
    queryRewriteDescription: '検索前に ContextDB が LLM でクエリを書き換えて再現性を高めます。公式の既定はオフ、本プラットフォームの既定はオン',
    toasts: {
      saveSuccess: '検索設定を保存しました',
      saveFailed: '設定の保存に失敗しました: {message}'
    }
  },
  defaultSettings: {
    saving: '保存中',
    loadFailed: 'デフォルト設定を読み込めませんでした。再試行してから編集してください。',
    title: 'デフォルト設定',
    readOnly: '変更できるのはワークスペース管理者のみです。現在有効な既定値は確認できます。',
    webSearchGroup: 'ウェブ検索',
    toasts: {
      saveFailed: '保存に失敗しました：{message}'
    },
    webSearch: {
      label: '既定の検索エンジン',
      description: '独自の検索エンジンを持たないエージェントでウェブ検索が有効なときに使われます。',
      unset: '既定の検索エンジンが未設定です。独自の検索エンジンを持たないエージェントはウェブ検索できません。',
      placeholder: '検索エンジンを選択'
    },
    hints: {
      workspace: 'ワークスペースの設定を使用中です。',
      system: '未設定。現在はシステム既定を使用中：{name}',
      auto: '未設定。現在は最初に利用可能なモデルを使用中：{name}',
      followChat: '未設定。既定のチャットモデルに従います：{name}',
      staleFallback: '選択したモデルは削除されたか利用できません。現在の代替：{name}',
      staleNone: '選択したモデルは削除されたか利用できず、代替できるモデルもありません。'
    },
    slots: {
      asr: {
        label: '既定の音声認識モデル',
        description: '音声・動画の文字起こしの既定の選択です。',
        none: '利用可能な音声認識モデルがないため、文字起こしは使えません。'
      },
      vlm: {
        label: '既定のビジョンモデル',
        description: '画像理解とマルチモーダル解析の既定の選択です。',
        none: '利用可能なビジョンモデルがないため、画像理解は使えません。'
      },
      rerank: {
        label: '既定の Rerank モデル',
        description: '独自のリランクモデルを持たない検索と組み込みエージェントで使われます。',
        none: '利用可能な Rerank モデルがないため、検索結果は取得順のまま返されます。'
      },
      embedding: {
        label: '既定の Embedding モデル',
        description: '新規ナレッジベース作成時に既定で選ばれます。既存のナレッジベースには影響しません。',
        none: '利用可能な Embedding モデルがないため、ナレッジベースを作成できません。'
      },
      utility: {
        label: '軽量生成モデル',
        description: 'セッションタイトル、MCP 利用説明などの短いテキスト生成に使います。高速で安価なモデルがおすすめです。',
        none: '利用可能なチャットモデルがないため、タイトルや説明を生成できません。'
      },
      chat: {
        label: '既定のチャットモデル',
        description: '新規エージェントと Q&A で使われ、バックグラウンド処理の代替モデルにもなります。',
        none: '利用可能なチャットモデルがないため、Q&A とバックグラウンド生成は使えません。'
      }
    }
  },
  envVarSettings: {
    host: {
      title: '環境変数'
    }
  },
  settings: {
    modelManagement: 'モデル管理',
    autoCheckUpdate: '更新の自動ダウンロード',
    autoCheckUpdateDesc: '有効にすると、バックグラウンドで最新バージョンを自動的に確認・ダウンロードします。',
    parserEngine: '解析エンジン',
    mcpService: 'MCPサービス',
    workspaceSettings: 'ワークスペース設定',
    capabilityUnavailable: 'この機能は現在のデプロイでは利用できません。利用可能なページに戻りました。',
    hostApprovalDefault: {
      title: '既定の実行権限の承認',
      description: 'エージェントがファイルを削除するとき、またはワークスペースの外へ書き込むときに、毎回確認するかモデルに承認させるかを決めます。新しいチャットはここから始まり、今のチャットは入力欄の左で切り替えられます。'
    },
    storage: {
      title: 'ストレージエンジン',
      engineLocal: 'ローカル',
      engineCos: 'Tencent Cloud COS',
      engineTos: 'Volcengine TOS',
      engineOss: 'Alibaba Cloud OSS'
    },
    parser: {
      title: '解析エンジン'
    },
    roleDenied: {
      title: '権限が不足しています',
      desc: '現在のロールではこの設定ページにアクセスできません。このワークスペースの管理者に必要なロールの付与を依頼してください。'
    },
    navGroups: {
      systemAdministration: 'システム管理'
    },
    skills: {
      nativeUsage: 'Select packages in the agent configuration. Scripts require OpenSandbox and suitable dependencies; a catalog entry does not prove dependencies are installed.',
      addSourceDescription: 'Import a directory containing one SKILL.md, references and scripts. Importing records content and does not execute an installer.',
      title: 'スキル管理',
      description: 'Manage skill packages. Selected instructions and references are loaded by SkillsMiddleware; uploading does not install dependencies.',
      helpTooltip: 'The catalog holds instructions, references and scripts. Scripts run in the session sandbox; dependencies come from its deployed image.',
      addSkill: 'スキルを追加',
      addStepRegister: '登録',
      addFileSelected: '{name}を選択しました',
      addClearFile: 'クリア',
      emptyDesc: 'No skill packages yet. Upload a ZIP or add a source.',
      deleteCatalog: 'カタログから削除',
      deleteCatalogConfirm: 'Delete “{name}” from the catalog? Historical installation records remain; referenced entries cannot be deleted.',
      deleteSuccess: 'カタログから削除しました',
      registerAccepted: 'カタログに追加しました',
      loadFailed: '読み込みに失敗しました'
    },
    sandbox: {
      title: 'サンドボックス設定',
      skillUploadClick: 'クリックしてzipバンドルをアップロード',
      skillUploadDrag: 'またはここにファイルをドロップ',
      skillSourceSection: 'ソースからインストール',
      skillSourceSectionHint: 'ClawHub、GitHub、SkillHubのリンク、または{\'@\'}owner/slugを貼り付けてください。バンドルのサイズは{size} MB以下にしてください。',
      skillUploadSection: 'ローカルのバンドルをアップロード',
      skillUploadSectionHint: 'SKILL.mdを含むzipを下にドロップするか、クリックしてファイルを選択してください。バンドルのサイズは{size} MB以下にしてください。',
      skillSourcePlaceholder: 'ClawHub: {\'@\'}owner/slug。GitHub / SkillHub: 完全なURLを貼り付け',
      skillSourceFailed: 'レジストリからのスキルのインストールに失敗しました',
      skillUploadFailed: 'スキルのアップロードに失敗しました',
      skillBundleTooLarge: 'スキルバンドルのサイズは{size} MBを超えることはできません。',
      skillBundleTooManyFiles: 'スキルディレクトリに含められるファイルは{count}個までです。',
      skillBundleTooManyZipEntries: 'アーカイブに含められるzipエントリは{count}個までです。',
      installCommandRunning: 'コマンド実行中',
      skillFiles: 'ファイルを表示',
      skillFilesTitle: 'ファイル',
      skillFilesEmpty: 'このスキルには参照できるファイルがまだありません。',
      skillFilesLoadFailed: 'スキルファイルの読み込みに失敗しました',
      skillFilesFileLoadFailed: 'このファイルを読み取れませんでした',
      skillFilesBinary: 'このファイルはバイナリのためプレビューできません。',
      skillFilesTruncated: 'ファイルが大きいため、先頭部分のみ表示しています。',
      skillFilesSelectHint: '左側でファイルを選択すると表示されます',
      skillFilesPreview: 'プレビュー',
      skillFilesSource: 'ソース',
      skillDisabled: 'スキルを無効にしました',
      installCommandWaiting: '出力を待っています。経過時間は更新されます。'
    }
  },
  agent: {
    taskLabel: 'タスク:',
    think: '思考中',
    copy: 'コピー',
    addToKnowledgeBase: 'ナレッジベースに追加',
    updatePlan: 'プランを更新',
    webSearchFound: 'Web検索結果を<strong>{count}</strong>件見つけました',
    toolFallback: 'ツール',
    stepsCompleted: '<strong>{steps}</strong>ステップ完了',
    reasoningRounds: '推論<strong>{rounds}</strong>回',
    earlierSteps: '完了したステップ {count} 件',
    viewReasoning: '思考を表示',
    toolCalls: 'ツール呼び出し<strong>{tools}</strong>回',
    durationSuffix: '<strong>{duration}</strong>',
    stepSummarySeparator: ' · ',
    contextCompacted: 'コンテキストを圧縮しました',
    contextCompactedSummary: '{before} → {after}トークン',
    contextCompactedDegraded: '要約を利用できないため、元の記録を保持しました',
    title: 'エージェント',
    subtitle: 'エージェントを設定・管理して、会話の動作と機能をカスタマイズします',
    createAgent: 'エージェントを作成',
    builtin: '組み込み',
    disabled: '無効',
    disable: '無効化',
    enable: '有効化',
    noDescription: '説明なし',
    selectAgent: 'エージェントを選択',
    noAgents: 'エージェントがありません',
    manageAgents: '管理',
    builtinAgents: '組み込みエージェント',
    customAgents: 'カスタムエージェント',
    selector: {
      title: 'エージェントを選択',
      current: '現在',
      goToSettings: '設定',
      sharedLabel: '共有',
      notReadyHint: '準備ができていません。設定が必要な項目: {items}',
      notReadyStatus: '設定が必要',
      configureAction: '設定を開く',
      sharedNotReadyContact: '共有元スペースの管理者に設定の完了を依頼してください',
      capabilitiesSection: '機能',
      webSearchCapability: 'Web検索',
      imageUploadCapability: '画像アップロード',
      capabilityEnabled: 'オン',
      capabilityDisabled: 'オフ',
      capabilitySupported: '対応',
      capabilityUnsupported: '非対応',
      capabilityUnconfigured: '未設定'
    },
    editor: {
      assistantChanged: 'アシスタントがこのエージェントを変更しました。最新の設定を確認するには、開き直してください。',
      assistantDeleted: 'アシスタントがこのエージェントを削除しました。',
      reasoningEffortUnsupported: '選択中のモデルは思考に対応していません。「オフ」以外は無視されます。',
      reasoningEffortAlwaysOn: '選択中のモデルは常に思考します。オフにはできず、強度のみ調整できます。',
      createTitle: 'エージェントを作成',
      editTitle: 'エージェントを編集',
      basicInfo: '基本情報',
      basicInfoDesc: 'エージェントの名前、説明、実行モードを設定します',
      promptsConfig: 'プロンプト',
      promptsConfigDesc: 'システム、コンテキスト、意図判定、リライト、フォールバックの各プロンプトを設定します',
      modelConfig: 'モデル設定',
      modelConfigDesc: 'チャットモデル、補助モデル（リランク）、生成パラメータを設定します',
      toolsConfig: 'ツール',
      toolsConfigDesc: 'エージェントが利用できるツールを設定します',
      knowledgeConfig: 'ナレッジベース',
      knowledgeConfigDesc: 'エージェントのナレッジベース範囲とFAQ戦略を設定します',
      agentId: 'エージェントID',
      agentIdDesc: 'API連携でエージェントを指定する際にこのIDを使用します',
      name: '名前',
      namePlaceholder: 'エージェント名を入力してください',
      nameRequired: 'エージェント名は必須です',
      systemPromptRequired: 'システムプロンプトは必須です',
      modelRequired: 'モデルを選択してください',
      queryMissingInRewrite: 'リライト用ユーザプロンプトには{\'{{\'}query{\'}}\'}プレースホルダが必要です',
      queryMissingInFallback: 'フォールバックプロンプトには{\'{{\'}query{\'}}\'}プレースホルダが必要です',
      description: '説明',
      descriptionPlaceholder: 'エージェントの説明を入力してください',
      normalDesc: '素早く応答し、直接回答します',
      agentDesc: '多段階の思考で、複雑な質問を深く分析します',
      model: 'モデル',
      modelPlaceholder: 'モデルを選択',
      systemPrompt: 'システムプロンプト',
      systemPromptPlaceholder: 'エージェントの動作と役割を定義するカスタムシステムプロンプト（{\'{{\'}web_search_status{\'}}\'}プレースホルダでWeb検索の挙動を動的に切り替えられます）',
      contextTemplateRequired: 'コンテキストテンプレートは必須です',
      temperature: 'Temperature',
      thinking: '思考モード',
      citationEnabled: '出典を表示',
      citationEnabledDesc: '最終回答にナレッジベースとWebの出典を表示します。無効にしても検索と根拠付けは機能します',
      mode: '実行モード',
      knowledgeBases: 'ナレッジベース',
      allKnowledgeBases: 'すべてのナレッジベース',
      selectedKnowledgeBases: '指定したナレッジベース',
      noKnowledgeBase: 'ナレッジベースなし',
      selectKnowledgeBases: 'ナレッジベースを選択',
      selectKnowledgeBasesDesc: '紐付けるナレッジベースを選択してください（共同利用のものを含む）',
      myKnowledgeBases: '自分のナレッジベース',
      sharedKnowledgeBases: '共同利用のナレッジベース',
      retrieveKBOnlyWhenMentioned: '指定された場合のみ検索',
      retrieveKBOnlyWhenMentionedDesc: 'オフ: 設定済みのナレッジベースを自動で検索します。オン: ユーザが{\'@\'}で指定した場合のみ検索します',
      rerankModel: 'リランクモデル',
      rerankModelDesc: 'ナレッジベースの検索結果を並べ替えて精度を高めます',
      rerankModelPlaceholder: 'リランクモデルを選択',
      rerankModelOptionalHint: '現在の範囲にRAG型のナレッジベースがないため任意です。後からRAG型ナレッジベースを追加した場合は、ワークスペースのデフォルトリランクモデルが自動的に使用されます。明示的に設定することを推奨します。',
      maxIterations: 'メインエージェントのモデル呼び出し上限',
      maxIterationsLimit: '上限あり',
      maxIterationsUnlimited: '無制限',
      allowedTools: '許可するツール',
      retrievalStrategy: '検索戦略',
      contextTemplate: 'コンテキストテンプレート',
      contextTemplatePlaceholder: 'カスタムコンテキストテンプレート...',
      queryUnderstandModel: 'クエリ理解モデル',
      queryUnderstandModelPlaceholder: '空欄の場合はメインのチャットモデルを使用します',
      rewritePromptSystem: 'リライト用システムプロンプト',
      rewritePromptSystemPlaceholder: '空欄の場合はデフォルトのプロンプトを使用します',
      rewritePromptUser: 'リライト用ユーザプロンプト',
      rewritePromptUserPlaceholder: '空欄の場合はデフォルトのプロンプトを使用します',
      maxCompletionTokens: '最大出力トークン数',
      maxCompletionTokensDefault: 'デフォルト',
      maxCompletionTokensCustom: 'カスタム',
      fallbackStrategy: 'フォールバック戦略',
      fallbackResponse: '固定応答',
      fallbackResponsePlaceholder: '申し訳ありませんが、この質問にはお答えできません。',
      fallbackPrompt: 'フォールバックプロンプト',
      fallbackPromptPlaceholder: '空欄の場合はデフォルトのプロンプトを使用します',
      skillsConfig: 'スキル',
      skillsSelection: 'スキル一覧',
      skillsAll: 'すべて',
      skillsSelected: '選択中',
      skillsNone: '無効',
      skillsGroupUnavailable: '利用不可',
      noSkillsAvailable: 'ワークスペースのカタログにスキルがまだありません。',
      goSandboxSettings: 'サンドボックスを管理',
      sandboxBackend: 'サンドボックス',
      memoryEnabled: '長期メモリ',
      nativeRuntime: {
        adoptRuntime: '現在の実行設定を適用',
        incompatible: 'この環境の実行方針と互換性のない値があります。以下の変更を確認してください。適用すると下書きだけが更新され、保存後に有効になります。',
        adoptQuick: '現在のネイティブ高速回答設定を適用',
        changesPending: '以下の変更は下書きに適用済みです。保存後に有効になります。',
        removed: 'フィールドを削除',
        defaultsUnavailable: '現在の実行既定値を取得できません。保存する前に再読み込みしてください。',
        retry: '再読み込み',
        resolveBeforeSave: '互換性のない設定を解決してから保存してください。',
        quickDesc: '高速回答はネイティブエージェントで必要に応じて検索し回答します。モデル呼び出し上限は個別に設定されます。',
        promptDesc: '現在のモードのシステム指示またはテンプレート参照を設定します'
      },
      postCreateHint: {
        title: '作成しました',
        footer: '引き続き設定を調整し、共有と公開チャネルを設定してから「保存して閉じる」をクリックしてください。'
      },
      buttons: {
        create: 'エージェントを作成',
        saveAndClose: '保存して閉じる'
      }
    },
    messages: {
      created: 'エージェントを作成しました',
      updated: 'エージェントを更新しました',
      deleted: 'エージェントを削除しました',
      deleteFailed: '削除に失敗しました',
      saveFailed: '保存に失敗しました',
      copied: 'エージェントをコピーしました',
      copyFailed: 'コピーに失敗しました',
      disabled: 'エージェントを無効化しました',
      enabled: 'エージェントを有効化しました'
    },
    delete: {
      confirmTitle: 'エージェントを削除',
      confirmMessage: 'エージェント「{name}」を削除してもよろしいですか？この操作は取り消せません。'
    },
    shareScope: {
      title: '共有範囲',
      desc: 'スペースのメンバーはこのエージェントを読み取り専用で利用し、現在の設定がそのまま適用されます。エージェントへの変更は共有先のスペースにも反映されます。スペースのメンバーがナレッジベースの内容を編集できるようにするには、ナレッジベースをスペースに共有してください。',
      knowledgeBase: 'ナレッジベース',
      chatModel: 'チャットモデル',
      rerankModel: 'リランクモデル',
      webSearch: 'Web検索',
      mcp: 'MCPサービス',
      kbAll: 'すべてのナレッジベース',
      kbSelected: '{count}件を指定',
      kbNone: '使用しない',
      modelConfigured: '設定済み',
      modelNotSet: '未設定',
      enabled: 'オン',
      disabled: 'オフ',
      mcpAll: 'すべてのサービス',
      mcpSelected: '{count}件を指定',
      mcpNone: '使用しない'
    },
    detail: {
      title: 'エージェントの詳細',
      useInChat: 'チャットで使用'
    },
    empty: {
      title: 'カスタムエージェントがありません',
      description: '右上のボタンをクリックして最初のエージェントを作成してください',
      sharedTitle: '共有されたエージェントはありません',
      sharedDescription: 'スペースに参加するか、他のユーザにエージェントの共有を依頼してください',
      favoritesTitle: 'お気に入りはありません',
      favoritesDescription: 'エージェントのカード右上にある星マークをクリックすると、お気に入りに追加できます',
      recentsTitle: 'まだ何もありません',
      recentsDescription: '最近使用したエージェントがここに表示されます'
    },
    sections: {
      builtin: '組み込み',
      mine: '自分が作成',
      tenantOthers: 'ワークスペース · 他のメンバー',
      tenantReadonly: 'ワークスペース · 閲覧のみ',
      sharedByMe: '自分が共有',
      sharedEditable: '共有された項目 · 編集可能',
      sharedReadonly: '共有された項目 · 閲覧のみ'
    },
    tabs: {
      sharedToMe: '共有された項目'
    },
    features: {
      webSearch: 'Web検索有効',
      knowledgeBase: 'ナレッジベース紐付け済み',
      mcp: 'MCPサービス有効',
      multiTurn: 'マルチターン会話'
    },
    mode: {
      normal: 'クイック回答',
      agent: 'スマート推論'
    },
    type: {
      normal: 'クイック回答',
      agent: 'スマート推論'
    },
    capabilities: {
      kbCount: 'ナレッジベース{count}件を指定',
      kbAll: 'すべてのナレッジベースにアクセス可能',
      mcpEnabled: 'MCPサービス有効',
      multiTurn: 'マルチターン会話'
    },
    artifactDrawer: {
      buttonTitle: 'この回答で生成されたファイルを表示',
      title: '生成されたファイル',
      empty: '今回のやり取りでダウンロード可能なファイルは生成されませんでした。',
      preview: 'プレビュー',
      previewBack: '一覧に戻る',
      collecting: '生成されたファイルを保存中…',
      delete: '削除',
      deleteTitle: 'このファイルを削除しますか？',
      deleteConfirm: '「{name}」と保存されている内容を完全に削除します。元に戻せません。',
      deleted: 'ファイルを削除しました',
      deleteFailed: '削除に失敗しました。再試行してください。',
      download: 'ダウンロード',
      downloadFailed: 'ダウンロードに失敗しました。再試行してください。',
      inlinePreviewHint: 'クリックしてプレビュー',
      inlineMissing: 'ファイルを利用できません',
      inlineDeleted: 'ファイルは削除されました'
    }
  },
  knowledgeStages: {
    expandBranch: '子項目を展開',
    collapseBranch: '子項目を折りたたむ',
    resizeDrawer: 'ドラッグしてパネル幅を調整',
    status: {
      pending: '保留中',
      running: '実行中',
      finalizing: '最適化中',
      done: '完了',
      failed: '失敗',
      skipped: 'スキップ済み',
      cancelled: 'キャンセル済み'
    },
    stage: {
      docreader: 'ドキュメント解析',
      chunking: 'チャンク分割',
      embedding: 'ベクトル化',
      multimodal: 'マルチモーダル認識',
      postprocess: '後処理'
    },
    stall: {
      title: '{minutes} 分間進捗がありません。停止している可能性があります'
    },
    processConfig: {
      title: '今回の解析設定'
    }
  },
  uploadConfirm: {
    imageEmbeddingModel: '画像インデックス用 Embedding モデル',
    imageIndexInherited: '画像インデックスにはナレッジベースの Embedding モデルを使用します。変更はナレッジベース設定で行ってください。',
    imageVectorIndex: '今回の画像ベクトル索引',
    imageVectorIndexHint: '今回のアップロードまたは再解析で画像ベクトルを生成します。ナレッジベースの既定設定は変更しません。検索への利用は画像ベクトル検索設定に従います。',
    imageVectorRequiresIndex: '先にナレッジベース設定でベクトル索引を有効にしてください。',
    documentSummary: 'ドキュメントの要約',
    documentSummaryDescription: '今回インポートするドキュメントの要約を自動生成するか選択します。',
    generateSummary: 'ドキュメントの要約を生成',
    generateSummaryHint: '既定で有効です。無効にすると要約生成をスキップし、解析、インデックス作成、その他の処理は設定どおり実行されます。',
    title: 'アップロードの確認',
    parseConfig: '解析設定',
    configNav: '解析設定のナビゲーション',
    navParserDefault: 'デフォルト',
    navParserCustomized: 'カスタム',
    moreOptions: 'その他の処理オプション',
    summaryParentChildShort: '親子チャンク',
    summaryParserForceScanned: 'スキャンモード',
    summaryQuestionCountValue: '{count}',
    summaryGraphTagsValue: '{count}',
    navChunkingSummary: 'チャンク{size}',
    statusOn: 'オン',
    statusOff: 'オフ',
    notSet: '未設定',
    summaryNoTags: '未設定',
    summaryTagsCount: 'タグ{count}件',
    confirm: 'アップロードして解析',
    cancel: 'キャンセル',
    tabTags: 'ドキュメントのタグ',
    tagsDescription: '今回のインポート対象すべてのドキュメントに付けるタグを選択してください',
    tagsPlaceholder: 'タグを選択（複数選択可）',
    tagsEmpty: 'このナレッジベースにはタグがありません。アップロード後にタグ管理から作成できます。',
    tagsLoadFailed: 'タグの読み込みに失敗しました。後からドキュメント一覧で設定できます。',
    noItems: 'ファイルまたはURLを1件以上追加してください',
    urlItemLabel: 'URL',
    urlAdded: 'URLを追加しました',
    urlDuplicate: 'このURLは既に一覧にあります',
    statusNeedsSetup: '設定が必要',
    multimodalSetupHint: '画像が含まれています。マルチモーダルを有効にしてモデルを選択してください。',
    asrSetupHint: '音声が含まれています。音声認識を有効にしてモデルを選択してください。',
    vlmModelRequired: 'マルチモーダルモデルを設定してください',
    asrModelRequired: '音声認識モデルを設定してください',
    vlmModelSelectRequired: 'マルチモーダルが有効です。VLMモデルを選択してください。',
    asrModelSelectRequired: '音声認識が有効です。ASRモデルを選択してください。',
    continueAdd: '続けて追加',
    destinationLabel: 'アップロード先',
    destinationChange: 'アップロード先を変更',
    filesAdded: '{count}件のファイルを追加しました',
    filesAllDuplicate: '選択したファイルは既に一覧にあります',
    titleManual: 'オンライン作成の確認',
    confirmManual: '作成して解析',
    titleReparse: '再解析の確認',
    confirmReparse: '確定して再解析',
    reparseSource: '再解析するドキュメント',
    reparseHint: '前回の解析設定を引き継ぎます。ここで変更できます',
    manualCharCount: '{count}文字',
    pdfForceScanned: {
      label: 'スキャンPDFとして強制解析',
      description: 'Web印刷、スキャン、画像が多いPDFに有効です。全ページを画像としてレンダリングし、OCR／VLMで処理します。処理時間とモデル費用が増える場合があります。'
    }
  },
  knowledgeBase: {
    videosFilteredNoVLM: '{count}件の動画ファイルをスキップしました（動画のアップロードには対応していません）',
    importURL: 'URLからインポート',
    addDocument: 'ドキュメントを追加',
    importURLTitle: 'URLからインポート',
    urlRequired: 'URLを入力してください',
    invalidURL: '有効なURLを入力してください',
    urlLabel: 'URLアドレス',
    urlPlaceholder: 'WebページのURLを入力してください。例: https://example.com',
    urlTip: 'さまざまなWebページの内容をインポートできます。システムがWebページからテキストを自動で抽出して解析します',
    channelLabel: '取得元チャネル',
    channelWeb: 'Web',
    channelApi: 'API',
    channelBrowserExtension: 'ブラウザ拡張機能',
    channelWechat: 'WeChat',
    channelWecom: 'WeCom',
    channelFeishu: 'Feishu',
    channelDingtalk: 'DingTalk',
    channelSlack: 'Slack',
    channelIm: 'IMチャネル',
    channelConfluence: 'Confluence',
    channelGitLab: 'GitLab',
    channelNextcloud: 'Nextcloud',
    channelSeafile: 'Seafile',
    channelIma: 'Tencent IMA',
    channelUnknown: '不明',
    selectedCount: '{count}件選択中',
    pdfDocFormat: 'pdf、doc形式のファイル、最大{size}MB',
    textMarkdownFormat: 'text、markdown形式のファイル、最大{size}MB',
    dragFileNotText: 'テキストやリンクではなくファイルをドラッグしてください',
    searchPlaceholder: 'ナレッジベースを検索...',
    noMatch: '該当するナレッジベースがありません',
    noKnowledge: '利用できるナレッジベースがありません',
    loadingFailed: 'ナレッジベースの読み込みに失敗しました',
    allFilesSkippedNoEngine: '利用可能な解析エンジンがないため、選択したすべてのファイルをスキップしました',
    filesSkippedNoEngine: '利用可能な解析エンジンがないため、{count}件のファイルをスキップしました',
    moveToFolder: {
      action: 'フォルダに移動',
      newFolderPlaceholder: '新しいフォルダ名',
      newFolderAddRoot: 'ルート直下に新しいサブフォルダ',
      newFolderAddUnder: '「{folder}」の下に新しいサブフォルダ',
      duplicate: 'そのフォルダは既に存在します'
    },
    folderTree: {
      title: 'フォルダ',
      rootRow: 'ルート'
    },
    sort: {
      title: '並び替え'
    },
    infoCard: {
      title: 'ナレッジベース情報'
    }
  },
  resourceOrigin: {
    mine: '自分',
    mineTooltip: '自分が作成',
    tenant: 'ワークスペース',
    tenantTooltip: 'このワークスペースの他のメンバーが作成',
    tenantTooltipWithCreator: '{creator}が作成',
    space: 'スペース',
    spaceTooltip: '共有スペース「{space}」から共有',
    spaceTooltipWithTenant: '共有スペース「{space}」から共有 · 提供元{tenant}',
    shared: '外部',
    sharedTooltip: '共有スペース経由で外部ワークスペースからアクセス'
  },
  listSpaceSidebar: {
    all: 'すべて',
    workspace: 'ワークスペース',
    spaces: '共有された項目',
    favorites: 'お気に入り',
    recents: '最近'
  },
  batchManage: {
    selectAll: 'すべて選択',
    cancel: 'キャンセル',
    delete: '会話を削除',
    deleteConfirmTitle: '会話を削除',
    deleteConfirmBody: '選択した{count}件の会話を削除してもよろしいですか？この操作は取り消せません。',
    deleteAllConfirmBody: 'すべての会話を削除してもよろしいですか？この操作は取り消せません。',
    deleteSuccess: '削除しました',
    deleteFailed: '削除に失敗しました。しばらくしてから再試行してください'
  },
  contextualGuide: {
    stepOf: '{current} / {total}',
    skip: 'スキップ',
    prev: '戻る',
    next: '次へ',
    done: 'OK',
    interactHint: 'ハイライトされた箇所をクリックして続行してください',
    chat: {
      steps: {
        done: {
          title: '準備完了',
          desc: 'アップロードしたドキュメントに関する質問を試して、根拠付きの回答を確認してみましょう。'
        },
        send: {
          title: '送信してチャットを開始',
          desc: '送信すると新しいセッションが作成されます。AIがナレッジベースを使って回答し、引用元の該当箇所を表示します。'
        },
        input: {
          title: '質問を入力',
          desc: '知りたいことを入力するか、上部の推奨質問をクリックするとすぐに始められます。'
        },
        kb: {
          title: 'ナレッジの範囲を選択',
          desc: '{\'@\'}をクリックして、ナレッジベースやファイルを1つ以上選択してください。選択した範囲のみが回答に使用され、未選択の場合は現在のエージェント設定が適用されます。'
        }
      }
    },
    kbDetail: {
      steps: {
        done: {
          title: '解析後に利用可能',
          desc: 'ドキュメントのインデックスが完了したら、チャットで{\'@\'}を使ってこのナレッジベースを指定すると、出典付きの回答が得られます。'
        },
        upload: {
          title: 'ドキュメントを追加',
          desc: 'このメニューから、ファイルやフォルダのアップロード、URLのインポート、オンラインでの作成ができます。'
        },
        intro: {
          title: 'このナレッジベースは空です',
          desc: '最初の項目を追加すると、検索やチャットで利用できます。対応形式のファイルをドラッグ＆ドロップすることもできます。'
        }
      }
    },
    agentCreate: {
      steps: {
        submit: {
          title: 'エージェントを保存',
          desc: 'ハイライトされた確認ボタンをクリックして完了してください。その後、チャットでこのエージェントを選択できます。'
        },
        navTools: {
          title: 'ツールとMCP（任意）',
          desc: 'スマート推論モードでは、検索やコード実行などの組み込みツールとMCPサービスを有効にできます。'
        },
        multimodal: {
          title: '添付ファイルのアップロードを有効化',
          desc: '画像と音声のアップロードおよび添付ファイルの解析ルールを設定します。画像アップロードを有効にする場合は、下でVLMを選択してください。'
        },
        navMultimodal: {
          title: '添付ファイルのアップロード（任意）',
          desc: 'チャットで画像、ドキュメント、音声を送信できるようになります。画像理解にはシステム設定でVLMが必要です。'
        },
        navWebsearch: {
          title: 'Web検索（任意）',
          desc: 'エージェントが外部検索を呼び出して最新情報を取得できるようにします。'
        },
        knowledge: {
          title: 'ナレッジの範囲',
          desc: '汎用アシスタントには「すべて」、特定領域には「指定」、「なし」の場合はモデル単体またはWeb検索に依存します。'
        },
        navKnowledge: {
          title: 'ナレッジベースを紐付け',
          desc: 'エージェントが検索できるナレッジの範囲を指定します。デフォルトはすべてのナレッジベースです。'
        },
        model: {
          title: 'モデルを選択',
          desc: '設定済みのチャットモデルから選択してください。無い場合は先にシステム設定で追加してください。'
        },
        navModel: {
          title: 'チャットモデルを紐付け',
          desc: 'すべてのエージェントには推論エンジンとしてKnowledgeQAモデルが必要です。'
        },
        name: {
          title: '名前と説明',
          desc: '分かりやすい名前を付けてください。スマート推論モードではデフォルトの名前が入力される場合があります。必要に応じて編集してください。'
        },
        agentType: {
          title: 'エージェントのタイプを選択',
          desc: 'プリセットを選ぶと、システムプロンプト、推奨ツール、ナレッジ範囲が自動入力されます（例: Wiki作成、データ分析）。用途に応じて切り替えると、名前と説明も併せて更新されます。'
        },
        mode: {
          title: '実行モードを選択',
          desc: 'シンプルなQ&Aには「クイック回答」、ツールと多段階の思考が必要な複雑なタスクには「スマート推論」を使用します。'
        }
      }
    },
    agentList: {
      steps: {
        create: {
          title: 'エージェントを作成',
          desc: 'エージェントはモデル、ナレッジベース、ツール、プロンプトを組み合わせた再利用可能なアシスタントです。ハイライトされた「エージェントを作成」ボタンをクリックしてください。'
        }
      }
    },
    kbCreate: {
      steps: {
        submit: {
          title: 'ナレッジベースを作成',
          desc: 'ナレッジベースを作成せずにガイドを終了するには「OK」をクリックしてください。準備ができたら名前を入力し、タイプとモデルを確認して「作成」をクリックしてください。'
        },
        faq: {
          title: 'FAQインデックス',
          desc: 'Q&Aペアのインデックス方法を選択してください。FAQ項目は作成後に追加できます。'
        },
        multimodalVllm: {
          title: 'VLMモデルを選択',
          desc: 'マルチモーダルにはVLMが必要です。一覧が空の場合はシステム設定から追加してください。'
        },
        multimodalToggle: {
          title: 'マルチモーダル解析を有効化',
          desc: '有効にすると、画像を含むアップロードを視覚言語モデルで処理し、検索精度を高めます。'
        },
        navMultimodal: {
          title: 'マルチモーダル／画像（任意）',
          desc: '図表やスキャン、画像が多く含まれ、視覚的な理解が必要なドキュメントの場合は有効にしてください。'
        },
        storage: {
          title: 'ストレージ（任意）',
          desc: '元ファイルの保存先（ローカルまたはオブジェクトストレージ）です。通常はワークスペースのデフォルト値で問題ありません。'
        },
        chunking: {
          title: 'チャンク分割（任意）',
          desc: '検索用にドキュメントを分割する方法です。デフォルトのチャンクサイズはRAG向けに調整済みで、通常は変更不要です。'
        },
        parser: {
          title: '解析エンジン（任意）',
          desc: 'PDFやOfficeファイルの解析方法です。ほとんどの場合はデフォルト値で問題ありません。OCRや特殊なレイアウトが必要な場合に調整してください。'
        },
        embedding: {
          title: '埋め込みモデル',
          desc: 'テキストをベクトル化して意味検索を可能にします。上記のベクトル／キーワードインデックスと連携します。'
        },
        llm: {
          title: 'チャット／要約モデル',
          desc: '要約と回答の生成に使用します。一覧が空の場合は、ドロップダウンから設定を開いてモデルを追加してください。'
        },
        navModels: {
          title: 'モデル設定（必須）',
          desc: 'ナレッジベースにはチャットモデルが必要で、検索にはさらに埋め込みモデルが必要です。左側の「モデル設定」を開いてください。'
        },
        indexing: {
          title: 'インデックス機能',
          desc: 'ベクトル検索とキーワード検索はデフォルトで有効です。Wikiやナレッジグラフのインデックスも有効にできます。検索モードは少なくとも1つ有効にしてください。'
        },
        name: {
          title: '名前を入力',
          desc: '「製品マニュアル」「サポートFAQ」のような分かりやすい名前を付けてください。説明は任意です。'
        },
        type: {
          title: 'タイプを選択',
          desc: 'ドキュメント型はPDFやWordなどのアップロード向け、FAQ型は質問と回答のペア向けです。タイプは後から変更できません。'
        }
      }
    },
    tenantModels: {
      needChatModelFirst: 'エージェントを作成する前に、チャットモデル（KnowledgeQA）を追加してください。',
      stepsAgent: {
        done: {
          title: '続いてエージェントを作成',
          desc: '保存したら設定を閉じ、「エージェントを作成」をクリックしてください。ウィザードでモード、ナレッジベース、添付ファイルのアップロード設定を行えます。'
        },
        addModel: {
          title: 'チャットモデルを追加',
          desc: '「モデルを追加」をクリックし、KnowledgeQAタイプを設定してください。'
        },
        intro: {
          title: 'まずチャットモデルを設定',
          desc: 'エージェントの作成にはKnowledgeQAモデルが少なくとも1つ必要です。システム設定から追加してください（Embeddingはナレッジベースにのみ必要です）。'
        }
      },
      steps: {
        done: {
          title: '設定後に続行',
          desc: 'モデルを保存したら設定を閉じ、「ナレッジベースを作成」をクリックしてください。ウィザードでタイプ、インデックス、モデルの紐付けを設定できます。'
        },
        addModel: {
          title: 'モデルを追加',
          desc: '「モデルを追加」をクリックし、KnowledgeQA（チャット）とEmbeddingの両タイプを設定してください。LiteユーザはOllama経由でローカルモデルを取得できます。'
        },
        intro: {
          title: 'まずモデルを設定',
          desc: 'ドキュメント型ナレッジベースには、チャットモデル（要約とQ&A用）と埋め込みモデル（ベクトル検索用）が少なくとも1つずつ必要です。システム設定から追加してください。'
        }
      }
    },
    kbList: {
      steps: {
        create: {
          title: '最初のナレッジベースを作成',
          desc: 'ナレッジベースにはドキュメントやFAQを格納します。下のハイライトされた「ナレッジベースを作成」ボタンをクリックすると、入力手順をご案内します。'
        }
      }
    }
  },
  newUserGuide: {
    stepOf: '{current} / {total}',
    skip: 'スキップ',
    prev: '戻る',
    next: '次へ',
    done: '完了',
    reopen: 'プロダクトツアー',
    steps: {
      done: {
        title: '準備完了',
        desc: '基本は以上です。あなただけのナレッジアシスタントを作り始めましょう。このツアーは、メニュー上部のユーザ名の横にあるヘルプボタンからいつでも見直せます。'
      },
      models: {
        title: 'モデルを設定',
        desc: '重要なステップです。モデル管理でチャットモデルや埋め込みモデルなどを追加すると、ナレッジベースとチャットが利用できるようになります。「モデルを追加」をクリックして始めましょう。'
      },
      settings: {
        title: 'アカウントと設定',
        desc: 'ここからアカウント、メンバー、システム設定を管理できます。このツアーは、メニュー上部のユーザ名の横にあるヘルプボタンからいつでも再開できます。'
      },
      agents: {
        title: '専用エージェントを作成',
        desc: 'ナレッジベース、プロンプト、ツールを組み合わせて、あなたの知見を活かした再利用可能なエージェントを作成できます。'
      },
      chat: {
        title: 'AIチャットを開始',
        desc: 'ナレッジベースに基づいて質問すると、出典付きの正確な回答が得られます。ここをクリックして新しいチャットを開始してください。'
      },
      knowledge: {
        title: 'ナレッジベースを作成',
        desc: 'すべてはここから始まります。ドキュメント、Webページ、FAQをアップロードすると、Xiaozhiが自動で解析してインデックスを作成します。ここをクリックしてナレッジベースを開いてください。'
      },
      welcome: {
        title: 'Xiaozhiへようこそ',
        desc: '数ステップでナレッジベース、チャット、エージェントの使い方をご紹介します。「次へ」をクリックして開始してください。'
      },
      assistant: {
        title: 'Xiaozhi アシスタントのご紹介',
        desc: 'Xiaozhi のバージョン、機能、設定について質問できます。現在のページをもとに、あなたの権限でエージェントの作成、定期タスクの設定、ナレッジの整理も行えます。'
      }
    }
  },
  assistantEntryGuide: {
    stepOf: 'v0.9.0 の新機能',
    skip: 'わかりました',
    interactHint: '強調表示された入口をクリックしてアシスタントを開いてみましょう。'
  },
  chatHeader: {
    automationTask: '自動化',
    moreActions: 'その他の会話操作',
    toggleSandboxPanel: 'サンドボックスターミナル',
    copyMarkdown: 'Markdownとしてコピー',
    deleteSession: '会話を削除',
    renamePlaceholder: '会話のタイトルを入力してください',
    temporaryWorkspace: '一時ワークスペース',
    markdownCopied: '会話全体をMarkdownとしてコピーしました',
    markdownCopyFailed: 'Markdownのコピーに失敗しました。再試行してください。',
    clearConfirmTitle: '会話のメッセージをクリア',
    clearConfirmBody: 'この会話のメッセージをすべてクリアしますか？会話自体は残りますが、この操作は取り消せません。',
    deleteConfirmTitle: '会話を削除',
    deleteConfirmBody: 'この会話を削除しますか？この操作は取り消せません。',
    deleteSuccess: '会話を削除しました',
    markdown: {
      sessionId: 'セッションID',
      exportedAt: 'エクスポート日時',
      user: 'ユーザ',
      assistant: 'アシスタント',
      attachments: '添付ファイル',
      references: '出典'
    },
    grants: {
      menu: '許可済みの操作',
      description: 'この会話で確認なしに許可された操作です。取り消すと次回また確認されます。',
      empty: '許可済みの操作はありません',
      revoke: '取り消す',
      revoked: '取り消しました',
      revokeFailed: '取り消しに失敗しました',
      loadFailed: '読み込みに失敗しました'
    }
  },
  menu: {
    sessionInProgress: '会話中',
    sessionUnread: '新しい回答',
    knowledgeBase: 'ナレッジベース',
    agents: 'エージェント',
    automations: 'オートメーション',
    artifacts: '成果物',
    organizations: '共有スペース',
    newChat: '新しいチャット',
    settings: 'システム設定',
    logout: 'ログアウト',
    clearMessages: 'メッセージをクリア',
    clearMessagesSuccess: 'メッセージをクリアしました',
    clearMessagesFailed: 'メッセージのクリアに失敗しました。しばらくしてから再試行してください',
    renameSession: 'タイトルを変更',
    renameSessionSuccess: 'タイトルを更新しました',
    renameSessionFailed: 'タイトルの更新に失敗しました。しばらくしてから再試行してください',
    batchManage: '一括管理',
    newSession: '新しいチャット',
    pin: 'ピン留め',
    unpin: 'ピン留めを解除',
    pinFailed: 'ピン留めに失敗しました。しばらくしてから再試行してください',
    unpinFailed: 'ピン留めの解除に失敗しました。しばらくしてから再試行してください',
    search: '検索',
    collapseSidebar: 'サイドバーを折りたたむ',
    expandSidebar: 'サイドバーを展開',
    myChats: 'マイチャット',
    apiChats: 'APIセッション',
    noSessions: '会話はまだありません'
  },
  resourceSort: {
    title: '並び替え',
    updatedTime: '更新日時',
    updatedTimeDescription: '既定の並び順です。',
    createdTime: '作成日時',
    createdTimeDescription: '新しく作成した項目や古い項目を確認',
    name: '名前',
    nameDescription: '名前が分かっている項目をすばやく検索',
    recentlyUpdated: '更新が新しい順',
    earliestUpdated: '更新が古い順',
    recentlyCreated: '作成が新しい順',
    earliestCreated: '作成が古い順',
    nameAscending: 'A–Z',
    nameDescending: 'Z–A'
  },
  artifactLibrary: {
    title: '成果物',
    subtitle: 'すべての会話でエージェントが生成したファイルをまとめて表示します',
    typeFilter: '種類で絞り込む',
    searchPlaceholder: 'ファイル名を検索',
    total: '{count} 件のファイル',
    versions: '{count} バージョン',
    preview: 'プレビュー',
    delete: '削除',
    deleteTitle: 'このファイルを削除しますか？',
    deleteConfirm: '「{name}」と保存されている内容を完全に削除します。元に戻せません。',
    deleteConfirmVersions: '「{name}」の全 {count} バージョンと保存されている内容を完全に削除します。元に戻せません。',
    deleted: 'ファイルを削除しました',
    deleteFailed: '削除に失敗しました。再試行してください。',
    download: 'ダウンロード',
    downloadFailed: 'ダウンロードに失敗しました。しばらくしてから再試行してください',
    openSession: '会話を開く',
    untitledSession: '無題の会話',
    loadMore: 'さらに読み込む',
    loadFailed: '成果物を読み込めませんでした',
    retry: '再試行',
    clearFilters: '絞り込みを解除',
    noMatches: {
      title: '一致するファイルがありません',
      description: '別のキーワードや種類をお試しください'
    },
    empty: {
      title: '成果物はまだありません',
      description: '会話でエージェントにレポートや表、スライドを作成させると、ここに表示されます'
    },
    groups: {
      today: '今日',
      yesterday: '昨日',
      last7Days: '過去 7 日間',
      last30Days: '過去 30 日間',
      earlier: 'それ以前'
    },
    categories: {
      all: 'すべて',
      document: 'ドキュメント',
      spreadsheet: 'スプレッドシート',
      presentation: 'プレゼンテーション',
      image: '画像',
      web: 'Web ページ',
      data: 'データ'
    }
  },
  localBrowser: {
    pipOpen: 'プレビューを別ウィンドウで表示',
    pipReturn: '会話内のプレビューに戻す',
    pipFailed: 'フローティングウィンドウを開けませんでした。もう一度お試しください。',
    captureScreenshot: 'スクリーンショットを取得',
    navigationIncomplete: 'ページの読み込みが指定の段階に達しませんでした。現在のページを確認してください。',
    noEntries: '記録はありません。',
    stopping: 'タスクを終了中…',
    elapsedSeconds: '{seconds} 秒',
    searchInstructionsTitle: 'ブラウザー検索の指示',
    searchInstructionsDescription: '使用する検索エンジンと検索 URL を設定します。',
    searchInstructionsHint: '保存後、次のリクエストから適用。空欄は既定値を使用します。',
    searchInstructionsReset: '既定値に戻す',
    searchInstructionsSaved: '保存しました',
    sourceHint: 'このターンはローカルブラウザでウェブページを調べ、操作します。ウェブ検索、ナレッジベース、他のツールと併用できます。',
    pressKey: 'キーを押す',
    hoverPage: '要素にホバー',
    scrollPage: 'ページをスクロール',
    focusElement: '要素にフォーカス',
    blurElement: 'フォーカスを外す',
    selectOption: '項目を選択',
    closeTab: 'タブを閉じる',
    runScript: 'ページスクリプトを実行',
    readConsole: 'コンソールを確認',
    readNetwork: 'ネットワーク要求を確認',
    resizeWindow: 'ウィンドウサイズを変更',
    emulateDevice: 'デバイスをエミュレート',
    actionPending: 'ブラウザーを操作中…',
    actionRecorded: 'ブラウザー操作を記録しました',
    untitledTab: '無題のタブ',
    contentTruncated: 'ページ内容の一部を表示しています。',
    controlScope: 'この会話のブラウザー操作のみを制御',
    pauseHint: 'ブラウザー操作を中断し、再開できるようページを保持します。会話は停止しません。',
    stopHint: 'このタスクが作成したタブを閉じ、借用したタブを返却します。ブラウザーと接続設定は保持します。',
    openPage: 'ページを開く',
    switchPage: 'ページを切り替え',
    readPage: 'ページを確認',
    listTabs: 'タブを一覧表示',
    clickPage: '要素をクリック',
    fillPage: '内容を入力',
    waitPage: 'ページを待機',
    openTab: 'タスクタブを作成',
    switchTab: 'タスクタブを切り替え',
    authorizeTab: 'タブの許可を要求',
    returnTab: 'タブを返却',
    needHelp: '操作が必要',
    browserAction: 'ブラウザー操作',
    actionFailed: '未完了',
    actionCompleted: '操作が完了しました',
    commandBusy: '前の操作が実行中です。完了までお待ちください。',
    invalidArguments: 'ブラウザーツールの引数が無効または不完全です。エージェントによる修正が必要です。',
    commandInterrupted: '操作が中断されました。ページを確認してプレビューから再開してください。',
    actionFailedHint: 'ブラウザー操作が完了しませんでした。ページを確認して再試行してください。',
    previewStale: '画面は未更新です',
    previewIdle: '最後の画面を保持しています',
    previewLive: '画面を同期中',
    previewLoading: '画面を取得中',
    borrowHint: '借用するページに切り替え、BrowserSkill の確認で許可または拒否を選択してください。許可後は自動で続行します。「操作を続行」は一時停止の解除のみで、借用の許可にはなりません。',
    helpHint: '確認または許可が必要です。プレビューをクリックして移動してください。',
    settingsTitle: 'ブラウザー接続',
    settingsDescription: 'BrowserSkill で手元の Chrome または Edge を接続すると、会話から実際のウェブページを操作できます。',
    openSettings: '接続設定を開く',
    settingsHint: 'ツールボックスで BrowserSkill を接続すると、ここでローカルブラウザーを利用できます。',
    unavailable: 'サーバーでローカルブラウザーが有効になっていません。管理者に連絡してください。',
    source: 'ブラウザーの接続先',
    sandbox: 'サンドボックス',
    local: 'ローカルブラウザー',
    paused: '一時停止中',
    connected: '接続済み',
    disconnected: '未接続',
    resume: '操作を再開',
    pause: '操作を一時停止',
    start: 'タスクを開始',
    stop: 'ブラウザータスクを終了',
    resumeShort: '再開',
    pauseShort: '一時停止',
    stopShort: '終了',
    pairHint: '拡張機能の「接続設定 → リモート接続」にリンクを貼り付け、サーバーを確認します。リンクは 5 分間有効で、1 回限り使用できます。',
    copyPairing: 'ペアリングリンクをコピー',
    copied: 'コピーしました',
    windowHint: 'タスクは独立したブラウザーのタスクウィンドウで実行されます。既存のタブを借りるには許可が必要です。',
    preview: 'ローカルブラウザーのプレビュー',
    waiting: 'タスクのページを待っています',
    startHint: 'ブラウザーへのリクエストで独立したタスクウィンドウが作成されます。',
    revoke: 'デバイスの認証を取り消す',
    revokeConfirm: '取り消すと、ローカルブラウザーを使うには再度ペアリングが必要です。',
    failed: '操作に失敗しました。再試行してください。',
    productDescription: 'エージェントがブラウザーでページを開き、内容を読み取り、操作できるオープンソースの Chrome / Edge 拡張機能です。',
    offline: 'オフライン',
    notPaired: '未ペアリング',
    lastSeen: '最終接続',
    readyHint: '準備完了。会話に戻り、ブラウザーで行うタスクを伝えてください。',
    capabilitiesTitle: 'エージェントができること',
    sidebarStatus: 'サイドバーに接続状態を表示',
    reconnectHint: '認証は保存されています。ブラウザーと拡張機能を開くと自動的に再接続します。',
    replaceDevice: 'ブラウザーを変更',
    installExtension: 'BrowserSkill をインストール',
    storeInstall: 'Chrome ウェブストア',
    edgeStoreInstall: 'Edge アドオン',
    extensionMinVersion: 'BrowserSkill v{version} 以降が必要です。Chrome と Edge に対応しています。',
    extensionOutdated: '拡張機能 v{current} は古いバージョンです。v{version} 以降に更新してください。',
    manualInstall: '手動インストール（代替手段）',
    storeInstallHint: 'Chrome ウェブストアまたは Edge アドオンから BrowserSkill をインストールし、ここに戻ってペアリングしてください。',
    installHint: 'ストアにアクセスできない場合やバージョンに互換性がない場合は、対応パッケージをダウンロードして手動でインストールできます。',
    downloadExtension: '対応パッケージをダウンロード',
    officialExtension: '公式拡張機能（Chrome ウェブストア）',
    installGuide: 'ダウンロードしたパッケージのインストール方法',
    pairGuide: 'ペアリングリンクの使い方',
    pairBrowser: 'ブラウザーを接続',
    packageUnavailable: '対応する拡張機能パッケージを管理者から入手してください。',
    manualCopy: '下のリンクをコピーしてください。有効期限は 5 分、使用は 1 回限りです。',
    pairingReady: 'コピーしました。5 分以内に拡張機能に貼り付けてください。1 回限り有効です。',
    copyAgain: '再コピー',
    usageTitle: '使い方',
    usageStep1Title: '拡張機能をインストール',
    usageStep1Text: 'ZIP を解凍し、ブラウザーのアドレスバーに chrome://extensions（Edge では edge://extensions）と入力します。「デベロッパーモード」を有効にし、「パッケージ化されていない拡張機能を読み込む」から解凍した拡張機能フォルダーを選択します。',
    usageStep2Title: 'ブラウザーをペアリング',
    usageStep2Text: 'ペアリングリンクを拡張機能の「接続設定 → リモート接続」に貼り付け、サーバーを確認します。同じスペースのすべての会話で共有されます。',
    usageStep3Title: '会話でタスクを伝える',
    usageStep3Text: 'ウェブタスクを送る前に、会話の入力欄で「ローカルブラウザー」をオンにしてください。ペアリングだけでは自動でオンになりません。タスクは独立したタスクウィンドウで実行されます。',
    usageStep4Title: 'プレビューで確認・再開',
    usageStep4Text: '会話に小さなプレビューが表示されます。クリックするとタスクタブに移動できます。中断したタスクは再接続後も一時停止するので、プレビューから再開してください。既存タブには許可が必要です。',
    running: '実行中',
    locateWindow: 'ブラウザーを表示',
    reconnectShort: '再接続を待機中'
  },
  toolbox: {
    title: 'ツールボックス',
    unavailable: '現在のワークスペースで利用できるツールはありません。'
  },
  automation: {
    conversationNotice: 'この会話は自動化タスクが実行します。手動でメッセージは送信できません。保留中のリクエストは上で対応してください。'
  },
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
  }
}
