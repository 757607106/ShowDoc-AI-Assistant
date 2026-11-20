export default {
  memorySettings: {
    kinds: {
      profile: '내 정보',
      preference: '선호',
      fact: '사실',
      task: '진행 중인 일',
      interest: '장기 관심사'
    },
    usage: {
      title: '기억이 사용되는 시점'
    }
  },
  imagePipeline: {
    smartocr: {
      name: '스마트',
      description: '먼저 이미지 특징을 관찰하여 설명을 생성하고, 그 특징을 바탕으로 OCR 실행 여부를 결정합니다. 모델 호출을 절약하고 분석 속도를 높입니다 이미지가 보정 가능한 문서나 라벨 사진으로 인식되면 인식 전에 페이지를 자동으로 정렬하고 잘라내어 OCR 정확도를 높입니다. 보정에 실패하면 원본 이미지를 사용합니다.',
      ocr: {
        thinking_enabled: {
          label: '문자 인식 시 사고 사용',
          description: '텍스트를 추출하기 전에 모델이 먼저 추론하도록 합니다. 일반적으로 사고는 필요하지 않습니다. 켜면 분석이 느려질 뿐 아니라 사고가 너무 길어져 본문이 잘려서 작업이 실패할 수 있습니다. 꼭 필요하다고 판단될 때만 켜세요.'
        }
      },
      observation: {
        thinking_enabled: {
          label: '설명 시 사고 사용',
          description: '이미지를 설명하고 속성을 보고하기 전에 모델이 먼저 추론하도록 합니다. 일반적으로 사고는 필요하지 않습니다. 켜면 분석이 느려질 뿐 아니라 사고가 너무 길어져 본문이 잘려서 작업이 실패할 수 있습니다. 꼭 필요하다고 판단될 때만 켜세요.'
        }
      },
      preprocess: {
        mode: {
          label: '문서 전처리',
          description: '기본값은 끄기입니다. 켜면 OCR 전에 페이지를 보정하고 잘라내므로 처리 시간이 늘어납니다. 자동: 관찰 결과로 판단 / 항상: OCR 대상으로 선택된 이미지를 매번 전처리합니다. 처리 중이거나 제한을 초과하면 원본 이미지를 사용합니다.',
          options: {
            auto: '자동',
            off: '끄기',
            always: '항상'
          }
        }
      },
      note_flow: {
        label: '관찰 결과가 결정합니다',
        description: '먼저 이미지를 설명하고 속성을 관찰한 뒤, 돌아온 속성이 OCR을 한 번 더 할 가치가 있는지 결정합니다. 페이지를 반듯하게 펴야 한다고 속성이 알리면 먼저 펴고 주변을 잘라낸 뒤 읽습니다. 그 단계를 쓸 수 없으면 원본 사진을 그대로 읽으며, 더 나빠지지 않습니다.'
      },
      ocr_on_unobserved: {
        label: '이미지 속성 관찰에 실패해도 OCR 실행',
        description: '모델이 이미지 속성을 올바르게 관찰하지 못하면 본문 텍스트 손실을 막기 위해 기본적으로 OCR을 실행합니다. 끄면 건너뜁니다. (4B 등 소형 비전 모델을 쓰거나, 사용자 지정 이미지 지시문이 시스템 프롬프트와 충돌할 때 관찰에 실패할 수 있습니다. 8B 이상은 실패 가능성이 낮아 끄지 않는 것을 권장합니다)'
      }
    },
    default: {
      name: '수동',
      description: '작업에 맞게 분석 동작 스위치를 직접 켜거나 끕니다.',
      ocr: {
        thinking_enabled: {
          label: 'OCR 시 사고 사용',
          description: '텍스트를 추출하기 전에 모델이 먼저 추론하도록 합니다. 일반적으로 사고는 필요하지 않습니다. 켜면 분석이 느려질 뿐 아니라 사고가 너무 길어져 본문이 잘려서 작업이 실패할 수 있습니다. 꼭 필요하다고 판단될 때만 켜세요.'
        }
      },
      caption: {
        thinking_enabled: {
          label: '설명 시 사고 사용',
          description: '설명을 쓰기 전에 모델이 먼저 추론하도록 합니다. 일반적으로 사고는 필요하지 않습니다. 켜면 분석이 느려질 뿐 아니라 사고가 너무 길어져 본문이 잘려서 작업이 실패할 수 있습니다. 꼭 필요하다고 판단될 때만 켜세요.'
        }
      },
      ocr_enabled: {
        label: '문자 인식',
        description: '이미지 속에 나타나는 텍스트를 추출합니다.'
      },
      caption_enabled: {
        label: '이미지 설명',
        description: '각 이미지에 대한 한 줄 설명을 생성해 캡션으로 저장합니다.'
      },
      note_actions: {
        label: '두 동작은 서로 독립적입니다',
        description: '각각 따로 켜고 끌 수 있습니다. 인식을 끄면 이미지는 여전히 설명되고, 설명을 끄면 글자는 여전히 추출됩니다. 둘 다 끄면 이미지가 아무것도 처리되지 않으므로 패널은 그 조합을 허용하지 않습니다.'
      }
    },
    errors: {
      noActionEnabled: '분석 동작을 하나 이상 켜세요. 모두 꺼져 있으면 아무것도 처리되지 않습니다.'
    }
  },
  imageAttr: {
    layout_upright: {
      label: '글자 방향',
      description: '이미지 속 글자가 똑바로 서 있는지. 기울거나 뒤집힌 페이지는 OCR 전에 바르게 펴는 것이 좋습니다.',
      values: {
        false: {
          label: '비정립',
          description: '회전·기울임 촬영·뒤집힘'
        },
        true: {
          label: '정립',
          description: '글자가 정상 방향'
        }
      }
    },
    layout_margin: {
      label: '여백',
      description: '내용 바깥(책상, 배경, 여백)이 화면 전체에서 차지하는 비율. 여백이 크면 OCR 전에 페이지를 더 타이트하게 잘라낼 수 있습니다.',
      values: {
        large: {
          label: '많음',
          description: '비텍스트 영역이 넓음 — 책상, 방, 거의 빈 페이지'
        },
        small: {
          label: '적음',
          description: '가장자리에 얇은 띠'
        },
        none: {
          label: '없음',
          description: '글자가 화면을 거의 채움'
        }
      }
    },
    contain_data_visual: {
      label: '데이터 시각화',
      description: '이미지가 차트, 그래프, 도표, 인포그래픽으로 데이터를 전달하는지 여부입니다. 글자가 적어 보여도 OCR 대상으로 유지합니다.',
      values: {
        false: {
          label: '아니오',
          description: '아니오 —— 사진, 삽화, 아이콘, 장식'
        },
        true: {
          label: '예',
          description: '예 —— 차트, 그래프, 도표'
        }
      }
    },
    contain_text: {
      label: '이미지 내 텍스트 양',
      description: '이미지 자체가 담고 있는 본문 텍스트의 양입니다. 텍스트를 읽기 위해 별도 OCR을 돌릴 가치가 있는지 판단합니다.',
      values: {
        block: {
          label: '문단 단위 본문',
          description: '문단 단위 본문 —— 스크린샷, 표, 문서 페이지'
        },
        sparse: {
          label: '약간의 글자',
          description: '약간의 글자만 —— 로고, 도로 표지판, 단일 라벨'
        },
        none: {
          label: '텍스트 없음',
          description: '텍스트가 전혀 없습니다'
        }
      }
    }
  },
  tenantInvitation: {
    errors: {
      notPending: '초대가 더 이상 대기 상태가 아닙니다.',
      forbidden: '초대 대상자만 수락 또는 거절할 수 있습니다.',
      notFound: '초대를 찾을 수 없거나 이미 취소되었습니다.',
      generic: '작업에 실패했습니다. 다시 시도해 주세요.'
    },
    myInbox: {
      title: '내 초대',
      description: '다른 워크스페이스의 초대 목록입니다.',
      empty: '대기 중인 초대가 없습니다.',
      acceptButton: '수락',
      declineButton: '거절',
      acceptSuccess: '"{tenant}"에 참여했습니다.',
      declineSuccess: '초대를 거절했습니다.',
      from: '초대자',
      tenantLabel: '워크스페이스',
      expiresIn: '만료: {date}',
      messageLabel: '메시지'
    }
  },
  tenantMember: {
    title: '멤버 관리',
    loading: '멤버를 불러오는 중…',
    retry: '다시 시도',
    audit: {
      action: {
        'rbac.member_added': '멤버 추가',
        'rbac.member_removed': '멤버 제거',
        'rbac.member_role_changed': '역할 변경',
        'rbac.member_left': '멤버 탈퇴',
        'rbac.access_denied': '접근 거부',
        'rbac.invitation_sent': '초대 전송',
        'rbac.invitation_accepted': '초대 수락',
        'rbac.invitation_declined': '초대 거절',
        'rbac.invitation_revoked': '초대 취소',
        'rbac.invitation_expired': '초대 만료'
      }
    },
    errors: {
      lastOwner: '마지막 소유자를 강등, 제거, 또는 떠날 수 없습니다. 다른 멤버를 먼저 소유자로 승격하세요.',
      generic: '오류가 발생했습니다. 다시 시도해 주세요.'
    },
    leave: {
      confirmTitle: '이 워크스페이스에서 나가시겠어요?',
      confirmBody: '이 워크스페이스의 모든 지식 베이스와 에이전트에 접근할 수 없게 됩니다. 나중에 다시 초대받을 수 있습니다.',
      confirm: '나가기',
      success: '워크스페이스에서 나갔습니다'
    },
    role: {
      owner: '소유자',
      admin: '관리자',
      contributor: '기여자',
      viewer: '뷰어'
    },
    permissions: {
      title: '역할 권한',
      desc: '각 역할이 이 워크스페이스에서 할 수 있는 작업입니다. 서버에서 적용되며 UI 컨트롤은 표시만 합니다.'
    }
  },
  userProfile: {
    title: '사용자 정보',
    description: '계정 기본 정보(사용자 ID, 사용자 이름, 계정, 가입 시각)를 확인하고 비밀번호를 변경할 수 있습니다.',
    changePassword: {
      label: '비밀번호 변경',
      description: '현재 비밀번호를 확인한 뒤 새 비밀번호를 설정합니다. 성공 시 모든 세션이 만료되어 다시 로그인해야 합니다.',
      currentLabel: '현재 비밀번호',
      currentPlaceholder: '현재 비밀번호를 입력하세요',
      currentRequired: '현재 비밀번호를 입력하세요',
      newLabel: '새 비밀번호',
      newPlaceholder: '새 비밀번호 입력',
      confirmLabel: '새 비밀번호 확인',
      confirmPlaceholder: '새 비밀번호를 다시 입력하세요',
      submit: '비밀번호 업데이트',
      success: '비밀번호가 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.',
      failed: '비밀번호 변경에 실패했습니다. 현재 비밀번호를 확인해 주세요.',
      policyFailed: '새 비밀번호는 8-32자이며 문자와 숫자를 포함해야 합니다',
      sameAsCurrent: '새 비밀번호는 현재 비밀번호와 같을 수 없습니다',
      oidcOnlyDescription: 'OIDC로 개설된 계정입니다. 로컬 로그인 비밀번호가 아직 설정되지 않았습니다.'
    }
  },
  credential: {
    configured: '구성됨',
    unconfigured: '구성되지 않음',
    configure: '구성',
    update: '교체',
    remove: '제거',
    inputPlaceholder: '값을 입력하세요',
    savedToast: 'credential이 저장되었습니다',
    saveFailed: 'credential 저장 실패',
    removedToast: 'credential이 제거되었습니다',
    removeFailed: 'credential 제거 실패',
    confirmRemovePrompt: '이 credential을 제거하시겠습니까? 이 작업은 되돌릴 수 없습니다.',
    confirmRemove: '제거 확인'
  },
  integrations: {
    claw: {
      title: 'WeKnora Skill'
    },
    chrome: {
      title: '지식 관리 어시스턴트'
    },
    agentEditor: {
      desc: 'IM 플랫폼 또는 웹사이트에 에이전트를 게시합니다. 통합 센터에서 관리하세요.'
    },
    embedOverview: {
      title: '웹 임베드 채널'
    },
    imOverview: {
      title: '연결된 IM'
    },
    api: {
      title: 'API 연동',
      updateApiKeyScopeFailed: 'API Key 업데이트 실패'
    },
    tabs: {
      im: 'IM 통합',
      embed: '웹 임베드',
      api: 'API 연동',
      chrome: 'Chrome 확장',
      cli: 'CLI',
      claw: 'Claw Skill',
      mcpserver: 'MCP 서버'
    },
    mcpserver: {
      title: 'MCP 서버',
      tools: {
        list_knowledge_bases: '지식 베이스 목록',
        list_knowledge_basesDesc: '범위 내 지식 베이스와 지원하는 검색 방식을 반환합니다',
        search_knowledge: '의미 검색',
        search_knowledgeDesc: '자연어 질문과 관련된 구절을 출처와 함께 찾습니다',
        grep_chunks: '키워드 / 정규식 검색',
        grep_chunksDesc: '원본 청크에 대한 대소문자 구분 없는 정규식 검색. 정확한 용어, 코드, 이름에 적합',
        list_documents: '문서 목록',
        list_documentsDesc: '지식 베이스의 문서를 페이지 단위로 나열합니다',
        read_document: '문서 읽기',
        read_documentDesc: '문서의 메타데이터와 청크를 순서대로 읽습니다',
        ask: '질문하기',
        askDesc: '엔드포인트에 설정된 에이전트를 실행하여 인용이 포함된 답변을 반환합니다. 후속 질문 지원',
        wiki_search: 'Wiki 검색',
        wiki_searchDesc: '생성된 Wiki 페이지를 검색합니다',
        wiki_read_page: 'Wiki 페이지 읽기',
        wiki_read_pageDesc: 'slug로 Wiki 페이지 하나를 읽습니다',
        wiki_index: 'Wiki 목차',
        wiki_indexDesc: '지식 베이스 Wiki의 목차를 표시합니다',
        add_document: '문서 추가',
        add_documentDesc: 'Markdown 텍스트 또는 URL로 문서를 추가합니다',
        update_document: '문서 업데이트',
        update_documentDesc: 'Markdown 문서의 내용 또는 제목을 교체합니다',
        delete_document: '문서 삭제',
        delete_documentDesc: '문서와 인덱스 데이터를 영구 삭제합니다'
      },
      groups: {
        retrieve: '검색 및 읽기',
        chat: '질의응답',
        wiki: 'Wiki',
        ingest: '쓰기 (신중하게 활성화)'
      }
    },
    cli: {
      title: 'WeKnora CLI'
    }
  },
  datasource: {
    title: '데이터 소스 관리',
    description: '외부 데이터 소스를 구성하여 콘텐츠를 지식베이스에 자동 동기화',
    add: '데이터 소스 추가',
    empty: '구성된 데이터 소스가 없습니다',
    edit: '편집',
    delete: '삭제',
    deleteConfirm: '이 데이터 소스를 삭제하시겠습니까? 동기화된 지식은 삭제되지 않습니다.',
    deleteSuccess: '데이터 소스가 삭제되었습니다',
    deleteFailed: '삭제 실패',
    syncNow: '지금 동기화',
    syncTriggered: '동기화 작업이 제출되었습니다',
    syncFailed: '동기화 트리거 실패',
    pause: '일시정지',
    resume: '재개',
    paused: '일시정지됨',
    resumed: '재개됨',
    pauseFailed: '일시정지 실패',
    logs: '로그',
    syncModeLabel: '동기화 모드',
    parseModeLabel: '구문 분석 모드',
    parseModeHint: 'Feishu 클라우드 문서의 구문 분석 방식입니다. 블록 분석은 더 빠르고 문서 내 첨부 파일을 유지합니다. 내보내기 분석은 docx로 변환하여 분석하며 이미지와 문서의 연관성이 더 잘 유지됩니다.',
    createTitle: '데이터 소스 추가',
    editTitle: '데이터 소스 편집',
    nameLabel: '이름',
    namePlaceholder: '데이터 소스 이름 입력',
    sectionBasic: '기본 정보',
    testConnection: '연결 테스트',
    testSuccess: '연결 성공',
    testFailed: '연결 실패',
    connected: '연결됨',
    connectionFailed: '연결 실패',
    isRequired: '은(는) 필수입니다',
    credentialsLabel: '자격 증명',
    resourceHint: '동기화할 공간/폴더를 선택하세요',
    untitled: '제목 없음',
    resourceLoadFailed: '리소스 목록 로드 실패',
    noResources: '동기화 가능한 위키 공간을 찾을 수 없습니다',
    noResourcesDesc: '앱이 콘텐츠를 가져오려면 그룹 채팅을 통해 위키 접근 권한을 얻어야 합니다',
    noResourcesDesc_notion: '앱이 콘텐츠를 가져오려면 Notion 페이지 접근 권한이 필요합니다',
    retryLoadResources: '다시 시도',
    guideStep1: 'Feishu에서 그룹 채팅을 만들고 그룹 설정의 \'그룹 봇\'에 앱을 추가하세요',
    guideStep2: '위키 \'설정\' > \'멤버 설정\' > \'멤버 추가\'를 열고 해당 그룹 채팅을 검색하여 추가하세요',
    guideStep3: '그룹 채팅 역할이 최소 \'읽기 가능\'인지 확인한 후, 돌아와서 다시 시도를 클릭하세요',
    guideStep1_notion: 'Notion에서 동기화하려는 페이지나 데이터베이스를 엽니다',
    guideStep2_notion: '오른쪽 상단의 \'···\' 메뉴를 클릭하고 \'Connect to\' 또는 \'Add connections\'를 선택합니다',
    guideStep3_notion: 'Integration 앱을 검색하여 선택한 후, 돌아와서 다시 시도를 클릭하세요',
    noResourcesDesc_nextcloud: '접근 가능한 폴더 또는 지원하는 파일이 없습니다',
    guideStep1_nextcloud: 'Nextcloud에 로그인하여 선택한 폴더의 읽기 권한을 확인하세요',
    guideStep2_nextcloud: '개인 설정 → 보안 → 장치 및 세션에서 앱 비밀번호를 만드세요',
    guideStep3_nextcloud: '여기서 인증 정보를 교체한 후 리소스를 다시 불러오세요',
    noResourcesDesc_seafile: '이 토큰으로 접근할 수 있는 라이브러리가 없거나 모두 암호화 라이브러리입니다(암호화 라이브러리는 동기화할 수 없음)',
    guideStep1_seafile: 'Seafile에 로그인하여 계정이 암호화되지 않은 라이브러리를 하나 이상 읽을 수 있는지 확인하세요',
    guideStep2_seafile: '\'설정 → Web API 토큰\'에서 토큰을 생성하거나 다시 생성하세요',
    guideStep3_seafile: '여기로 돌아와 새 토큰을 입력하고 다시 시도를 클릭하세요',
    permissionDocLink: '페이슈 위키 권한 설정 문서 보기',
    syncScheduleLabel: '동기화 주기',
    conflictLabel: '충돌 전략',
    syncDeletions: '삭제 동기화 (소스에서 삭제 시 지식베이스에서도 삭제)',
    createAndSync: '생성 후 즉시 동기화',
    createAndSyncSuccess: '데이터 소스가 생성되었으며 동기화 작업이 제출되었습니다',
    createButSyncFailed: '데이터 소스가 생성되었으나 동기화 트리거에 실패했습니다',
    updateSuccessSyncHint: '데이터 소스가 업데이트되었습니다. 편집은 자동으로 동기화를 시작하지 않으므로 다시 가져오려면 동기화를 클릭하세요.',
    saveFailed: '저장 실패',
    syncHistory: '동기화 이력',
    refreshLogs: '로그 새로고침',
    noLogs: '동기화 기록이 없습니다',
    comingSoon: '곧 지원 예정',
    docHint: '다음에서 인증 정보를 받으세요:',
    openDoc: '문서 열기',
    prereqBarText: '처음 사용하시나요? 클릭하여 Feishu 앱 설정 가이드를 확인하세요',
    prereqBarText_yuque: '처음 사용하시나요? 클릭하여 Yuque Token 설정 가이드를 확인하세요',
    prereqStep1Brief_yuque: 'Yuque 개인 Token 생성',
    prereqStep1Desc_yuque: 'Yuque 로그인 → 프로필 아이콘 → 설정 → Token → 새 Token 만들기',
    prereqStep2Brief_yuque: 'Token에 필요한 권한 부여',
    prereqStep2Desc_yuque: '최소한 repo:read 와 doc:read 를 선택하세요 (지식베이스 및 문서 콘텐츠 읽기)',
    prereqStep3Brief_yuque: '(선택) Enterprise 사용 시 Base URL 입력',
    prereqStep3Desc_yuque: '퍼블릭 클라우드 사용자는 입력하지 않아도 됩니다. Yuque Enterprise 또는 사설 배포 시 기업 도메인을 입력하세요',
    prereqStep1Brief_feishu: 'Feishu 커스텀 앱 생성',
    prereqStep1Desc_feishu: 'Feishu Open Platform 로그인 → 엔터프라이즈 커스텀 앱 생성',
    prereqStep2Brief_feishu: '봇 기능 추가',
    prereqStep2Desc_feishu: 'Open Platform → 앱 → 앱 기능 추가 → 봇',
    prereqStep3Brief_feishu: '앱 권한 구성',
    prereqStep3Desc_feishu: 'wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly 권한 활성화',
    prereqStep1Brief_lark: 'Lark 커스텀 앱 생성',
    prereqStep1Desc_lark: 'Lark Open Platform 로그인 → 엔터프라이즈 커스텀 앱 생성',
    prereqStep2Brief_lark: '봇 기능 추가',
    prereqStep2Desc_lark: 'Open Platform → 앱 → 앱 기능 추가 → 봇',
    prereqStep3Brief_lark: '앱 권한 구성',
    prereqStep3Desc_lark: 'wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly 권한 활성화',
    prereqStep1Brief_feishu_drive: 'Feishu 커스텀 앱 생성',
    prereqStep1Desc_feishu_drive: 'Feishu Open Platform 로그인 → 엔터프라이즈 커스텀 앱 생성',
    prereqStep2Brief_feishu_drive: '봇 기능 추가',
    prereqStep2Desc_feishu_drive: 'Open Platform → 앱 → 앱 기능 추가 → 봇',
    prereqStep3Brief_feishu_drive: '앱 권한 구성',
    prereqStep3Desc_feishu_drive: 'drive:drive:readonly, drive:export:readonly, docx:document:readonly 권한 활성화',
    prereqStep1Brief_lark_drive: 'Lark 커스텀 앱 생성',
    prereqStep1Desc_lark_drive: 'Lark Open Platform 로그인 → 엔터프라이즈 커스텀 앱 생성',
    prereqStep2Brief_lark_drive: '봇 기능 추가',
    prereqStep2Desc_lark_drive: 'Open Platform → 앱 → 앱 기능 추가 → 봇',
    prereqStep3Brief_lark_drive: '앱 권한 구성',
    prereqStep3Desc_lark_drive: 'drive:drive:readonly, drive:export:readonly, docx:document:readonly 권한 활성화',
    prereqOpenConsole_yuque: 'Yuque Token 설정으로 이동',
    yuqueFolderModeLabel: '폴더 구조',
    yuqueFolderModeToc: 'Yuque 목차대로 계층 구성',
    yuqueFolderModeNone: '루트에 평면 배치',
    yuqueFolderModeHint: 'Yuque 목차 계층에 따라 문서를 배치합니다. 참고: 이후 지식베이스에서 직접 옮긴 폴더는 해당 문서가 다음에 동기화될 때 Yuque 구조로 덮어써집니다.',
    yuqueTOCOnly: 'Yuque 목차에 표시되는 문서만 동기화',
    yuqueTOCOnlyHint: '"Yuque 목차대로 계층 구성"을 선택해야 동작합니다. 이미 지식베이스에 있는 문서는 그대로 유지되며, Yuque 목차에 없는 문서는 새로 추가되지 않을 뿐 삭제되지 않습니다.',
    dingtalkIngestLabel: 'DingTalk 수집 범위',
    dingtalkIncludeUploadedFiles: '업로드 파일(docx / pptx / xlsx / pdf) 수집',
    dingtalkIncludeUploadedFilesHint: '기본값은 꺼짐입니다. 켜면 선택한 범위에 업로드된 Word / PowerPoint / Excel / PDF 파일을 내려받아 파싱해 지식베이스에 넣습니다(파일당 최대 64 MiB). 본문은 저장소와 임베딩 비용에 포함됩니다. 꺼져 있으면 해당 파일은 건너뛰고 동기화 로그에 스위치가 꺼져 있다고 기록되며, 이미 지식베이스에 있는 사본은 삭제되지 않습니다.',
    prereqBarText_dingtalk: '처음 사용하시나요? 클릭하여 DingTalk 앱 설정 가이드를 확인하세요',
    prereqStep1Brief_dingtalk: '기업 내부 앱 생성',
    prereqStep1Desc_dingtalk: 'DingTalk Open Platform에서 기업 내부 앱을 생성하고 Client ID와 Client Secret을 복사하세요.',
    prereqStep2Brief_dingtalk: '지식베이스 읽기 권한 부여',
    prereqStep2Desc_dingtalk: 'Wiki.Workspace.Read, Wiki.Node.Read, Storage.File.Read 권한을 부여하세요.',
    prereqStep3Brief_dingtalk: '운영자 Union ID 입력',
    prereqStep3Desc_dingtalk: '대상 지식베이스에 접근할 수 있는 DingTalk 사용자의 Union ID를 입력하세요.',
    prereqOpenConsole_dingtalk: 'DingTalk 개발자 콘솔 열기',
    prereqBarText_ima: '처음 사용하시나요? 클릭하여 Tencent IMA OpenAPI 설정 가이드를 확인하세요',
    prereqStep1Brief_ima: 'IMA 에이전트 OpenAPI 액세스 활성화',
    prereqStep1Desc_ima: 'https://ima.qq.com/agent-interface 에 로그인하여 OpenAPI 액세스를 신청하세요',
    prereqStep2Brief_ima: 'ClientID 및 APIKey 획득',
    prereqStep2Desc_ima: '에이전트 접속 페이지에서 ima-openapi-clientid 와 ima-openapi-apikey 자격 증명을 복사하세요',
    prereqStep3Brief_ima: '대상 지식베이스에 자격 증명 권한 부여',
    prereqStep3Desc_ima: 'IMA 클라이언트에서 동기화하려는 지식베이스에 대해 자격 증명을 승인하세요. 승인되지 않은 지식베이스는 목록에 나타나지 않습니다',
    prereqOpenConsole_ima: 'Tencent IMA OpenAPI 콘솔로 이동',
    prereqBotBrief: '앱에 \'봇\' 기능 추가',
    prereqBotDesc: '오픈 플랫폼 → 앱 기능 추가 → 봇 → 버전 생성 후 게시',
    prereqPermBrief: 'API 권한 활성화',
    prereqOpenConsole: 'Feishu 오픈 플랫폼 설정으로 이동',
    prereqMemberBrief: '그룹 채팅을 통해 지식베이스 멤버로 추가',
    prereqMemberDesc: '그룹 채팅 생성 → 앱을 그룹 봇으로 추가 → 그룹 채팅을 지식베이스 멤버로 추가',
    back: '이전',
    next: '다음',
    save: '저장',
    schedule30min: '30분마다',
    schedule1h: '매시간',
    schedule6h: '6시간마다',
    schedule12h: '12시간마다',
    schedule24h: '매일',
    neverSynced: '동기화되지 않음',
    justNow: '방금',
    minutesAgo: '{n}분 전',
    hoursAgo: '{n}시간 전',
    daysAgo: '{n}일 전',
    syncError: {
      dingtalk_document_failed: 'DingTalk 문서를 읽을 수 없습니다. 접근 권한을 확인하고 동기화를 다시 시도하세요.',
      dingtalk_document_too_large: 'DingTalk 파일이 64 MiB 다운로드 제한을 초과하여 이번 동기화에서 건너뛰었습니다. 압축하거나 분할해 주세요.',
      dingtalk_resource_failed: 'DingTalk 리소스를 사용할 수 없습니다. 접근 권한과 선택한 리소스를 확인한 후 다시 시도하세요.',
      deletion_lookup_failed: '삭제 전 항목 조회에 실패했습니다. 서버 로그를 확인하세요',
      deletion_failed: '삭제에 실패했습니다. 서버 로그를 확인하세요',
      ingest_failed: '가져오기에 실패했습니다. 서버 로그를 확인하세요',
      nextcloud_permission_denied: 'Nextcloud 파일 접근이 거부되었습니다. 계정 권한을 확인하세요.',
      nextcloud_not_found: '목록 조회 후 Nextcloud 파일이 사라졌습니다. 다음 동기화에서 재시도합니다.',
      nextcloud_file_too_large: 'Nextcloud 파일이 MAX_FILE_SIZE_MB 제한을 초과합니다.',
      nextcloud_empty_file: 'Nextcloud 파일이 비어 있어 건너뛰었습니다.',
      nextcloud_source_changed: '다운로드 중 Nextcloud 파일이 변경되었습니다. 다음 동기화에서 재시도합니다.',
      nextcloud_invalid_response: 'Nextcloud WebDAV 응답이 잘못되었거나 불완전합니다.',
      nextcloud_ssrf_blocked: 'SSRF 정책이 Nextcloud 요청을 차단했습니다. SSRF_WHITELIST를 확인하세요.',
      nextcloud_fetch_failed: 'Nextcloud 파일을 가져오지 못했습니다. 다음 동기화에서 재시도합니다.',
      seafile_permission_denied: 'Seafile 파일에 접근할 수 없습니다. 토큰 소유자의 라이브러리 권한을 확인하세요.',
      seafile_not_found: 'Seafile 파일이 존재하지 않거나 이동되었습니다. 다음 동기화에서 다시 시도합니다.',
      seafile_file_too_large: 'Seafile 파일이 크기 제한을 초과합니다. MAX_FILE_SIZE_MB를 늘리거나 파일을 줄이세요.',
      seafile_empty_file: 'Seafile 파일이 비어 있어 건너뛰었습니다.',
      seafile_source_changed: '가져오는 동안 Seafile 파일이 변경되었습니다. 다음 동기화에서 다시 시도합니다.',
      seafile_invalid_response: 'Seafile이 해석할 수 없는 응답을 반환했습니다. 서버 버전과 리버스 프록시 설정을 확인하세요.',
      seafile_ssrf_blocked: 'Seafile 다운로드 URL이 SSRF 정책에 의해 차단되었습니다. fileserver 호스트를 SSRF_WHITELIST에 추가하세요.',
      seafile_fetch_failed: 'Seafile에서 파일을 가져오지 못했습니다. 다음 동기화에서 다시 시도합니다.'
    },
    resourceType: {
      wikiSpace: '위키 공간',
      docCategory: '문서 태그',
      book: 'Yuque 지식베이스',
      library: 'Seafile 라이브러리'
    },
    scheduleHuman: {
      '30min': '30분마다',
      '1h': '매시간',
      '6h': '6시간마다',
      '12h': '12시간마다',
      '24h': '매일'
    },
    confluence: {
      cloudFolderLimitation: 'Confluence Cloud는 아직 스페이스 최상위 폴더 등 컨테이너 아래의 페이지를 여기에 나열할 수 없습니다. 스페이스 전체를 선택하면 함께 동기화됩니다.'
    },
    field: {
      appId: 'App ID',
      appSecret: 'App Secret',
      clientId: 'Client ID',
      clientSecret: 'Client Secret',
      operatorId: '운영자 Union ID',
      operatorIdHint: '대상 지식베이스에 접근할 수 있는 DingTalk 사용자의 Union ID를 입력하세요.',
      integrationToken: 'Integration Token',
      apiToken: 'API Token',
      confluenceEdition: 'Confluence 에디션',
      confluenceEditionServer: 'Server / Data Center',
      confluenceEditionCloud: 'Cloud',
      confluenceBaseUrl: 'Confluence URL',
      confluenceUsername: '사용자 이름 또는 이메일',
      confluencePat: 'Server/DC 개인 액세스 토큰(PAT)',
      confluencePatHint: '선택 사항입니다. 입력하면 Bearer 인증을 사용하며 사용자 이름과 비밀번호가 필요하지 않습니다.',
      confluencePassword: 'Server/DC 비밀번호',
      confluenceApiToken: 'Cloud API 토큰',
      imaClientId: 'IMA ClientID',
      imaApiKey: 'IMA APIKey',
      baseUrl: 'Base URL',
      baseUrlHint: '비워두면 기본 퍼블릭 클라우드 주소가 사용됩니다. 프라이빗/엔터프라이즈 배포거나 리버스 프록시를 통해 액세스해야 하는 경우 사용자 정의 주소를 입력하세요 (예: https://api-proxy.example.com)',
      feedUrls: '피드 주소',
      feedUrlsHint: '한 줄에 하나씩 RSS / Atom 피드 주소를 입력하세요. 여러 개를 함께 입력할 수 있습니다.',
      authHeaders: '사용자 지정 헤더 (선택)',
      authHeadersHint: '비공개 피드 접근용. 한 줄에 하나씩 「이름: 값」 형식으로 입력하세요. 예: Authorization: Bearer xxxx'
    },
    drive: {
      folderTokenLabel: '드라이브 폴더 토큰',
      folderTokenPlaceholder: 'folder_token 또는 페이슈 드라이브 폴더 URL 입력',
      folderTokenRequired: '구체적인 폴더의 folder_token을 입력하세요. 클라우드 루트는 지원되지 않습니다',
      rootNotSupportedHint: '루트 폴더는 페이지네이션되지 않고 바로가기를 반환하지 않습니다. 구체적인 폴더를 선택하세요',
      load: '로드',
      shareHint: '앱이 접근할 수 있도록 먼저 드라이브 폴더를 앱이 속한 그룹에 공유하세요',
      placeholderTitle: '먼저 드라이브 폴더를 로드하세요',
      placeholderDesc: '위에 folder_token(또는 페이슈 드라이브 폴더 URL)을 입력하고 \'로드\'를 클릭하세요',
      loadForbiddenHint: '앱이 이 폴더에 접근할 수 없습니다. 페이슈 드라이브에서 폴더를 앱이 속한 그룹에 공유한 후 다시 시도하세요.',
      loadAuthHint: '앱 자격 증명이 유효하지 않거나 드라이브 권한이 없습니다. App ID / App Secret 및 drive:drive:readonly 권한을 확인하세요.',
      loadNotFoundHint: 'folder_token이 존재하지 않거나 삭제되었습니다. 페이슈 드라이브 폴더 URL에서 복사한 토큰이 맞는지 확인하세요.'
    },
    connectorDesc: {
      feishu: '페이슈 위키에서 문서, 스프레드시트, 파일 동기화',
      lark: 'Lark 위키에서 문서, 스프레드시트, 파일 동기화',
      feishu_drive: '페이슈 드라이브 폴더에서 문서, 스프레드시트, 파일 동기화',
      lark_drive: 'Lark 드라이브 폴더에서 문서, 스프레드시트, 파일 동기화',
      notion: 'Notion에서 페이지 및 데이터베이스 동기화',
      confluence: 'Confluence 스페이스와 페이지를 Markdown으로 동기화',
      yuque: '위큐 지식베이스에서 문서 동기화',
      dingtalk: 'DingTalk 지식베이스의 온라인 문서 동기화',
      rss: 'RSS / Atom 피드에서 글 동기화',
      ima: 'Tencent IMA 지식베이스에서 문서, 노트 및 파일 동기화 (AI 세션과 동영상 분석은 지원되지 않음)',
      gitlab: 'GitLab 프로젝트의 파일 동기화',
      nextcloud: 'WebDAV로 Nextcloud 폴더와 파일 동기화',
      seafile: 'Seafile 라이브러리의 폴더와 파일 동기화'
    },
    connector: {
      feishu: '페이슈 (Feishu)',
      lark: 'Lark (Feishu 글로벌)',
      feishu_drive: '페이슈 드라이브',
      lark_drive: 'Lark 드라이브',
      notion: 'Notion',
      confluence: 'Confluence',
      yuque: '위큐 (Yuque)',
      dingtalk: 'DingTalk 문서',
      rss: 'RSS / Atom 피드',
      ima: 'Tencent IMA',
      gitlab: 'GitLab',
      nextcloud: 'Nextcloud',
      seafile: 'Seafile'
    },
    logDetail: {
      startTime: '시작 시간',
      endTime: '종료 시간',
      failedItems: '실패한 문서',
      failedItemsMore: '표시되지 않은 실패 문서 {n}개',
      docsFailedSummary: '문서 {n}개 동기화 실패'
    },
    logSummary: {
      total: '총 횟수',
      success: '성공',
      failed: '실패',
      items: '동기화 항목'
    },
    logMetric: {
      total: '총계',
      skipped: '건너뜀',
      failed: '실패'
    },
    logStatus: {
      running: '동기화 중',
      success: '성공',
      partial: '부분 성공',
      failed: '실패',
      canceled: '취소됨'
    },
    step: {
      selectType: '유형 선택',
      credentials: '인증 정보',
      resources: '리소스 선택',
      strategy: '동기화 전략'
    },
    conflict: {
      overwrite: '덮어쓰기',
      skip: '기존 항목 건너뛰기'
    },
    seafile: {
      baseUrl: 'Seafile URL',
      apiToken: 'API 토큰',
      apiTokenHint: 'Seafile의 \'설정 → Web API 토큰\'에서 생성하세요. 계정에 선택한 라이브러리의 읽기 권한만 있으면 되며 토큰은 파일 다운로드 요청에 전송되지 않습니다.',
      singleLibraryOnly: '데이터 소스 하나는 라이브러리 하나만 동기화합니다. 다른 라이브러리를 선택하기 전에 현재 선택을 해제하세요.',
      selectionRequired: '라이브러리, 폴더 또는 파일을 하나 이상 선택하세요'
    },
    nextcloud: {
      baseUrl: 'Nextcloud URL',
      baseUrlHint: 'https://nextcloud.example.com/cloud 같은 설치 주소를 입력하세요. /remote.php/dav는 포함하지 않습니다. 사설 배포는 기존 SSRF_WHITELIST를 설정하세요.',
      username: '사용자 이름',
      appPassword: '앱 비밀번호',
      appPasswordHint: '개인 설정 → 보안 → 장치 및 세션에서 앱 비밀번호를 만들고 생성된 사용자 이름과 앱 비밀번호를 사용하세요.',
      selectionRequired: '폴더 또는 파일을 하나 이상 선택하세요',
      includeExtensions: '포함할 확장자 (선택)',
      excludeExtensions: '제외할 확장자 (선택)',
      extensionsHint: '.pdf, .md처럼 쉼표로 구분하세요. 포함 항목이 비어 있으면 지원하는 모든 형식을 동기화합니다. 제외가 우선하며 필터 변경은 삭제 대조 범위에도 영향을 줍니다.'
    },
    gitlab: {
      baseUrl: 'GitLab URL',
      accessToken: '개인 액세스 토큰',
      projects: 'GitLab 프로젝트',
      projectsHint: '프로젝트 ID 또는 네임스페이스 경로(예: group/project)를 입력하고, 필요에 따라 브랜치와 디렉터리를 지정하세요.',
      project: '프로젝트',
      projectId: '프로젝트 ID',
      projectIdPlaceholder: '예: 12345 또는 group/project',
      ref: '브랜치',
      refPlaceholder: '비워 두면 기본 브랜치를 사용합니다',
      paths: '디렉터리',
      pathsPlaceholder: '한 줄에 하나씩 입력하세요. 비워 두면 전체 프로젝트를 동기화합니다',
      addProject: '프로젝트 추가',
      projectRequired: 'GitLab 프로젝트를 하나 이상 추가하세요'
    },
    status: {
      active: '연결됨',
      paused: '일시정지',
      error: '오류'
    },
    syncMode: {
      incremental: '증분 동기화',
      full: '전체 동기화'
    },
    parseMode: {
      inherit: '서버 설정 사용',
      blocks: '블록 분석 (기본값)',
      export: '내보내기 분석 (docx)'
    }
  },
  mermaid: {
    diagram: '다이어그램',
    expand: '전체 화면',
    zoomIn: '확대',
    zoomOut: '축소',
    reset: '초기화',
    download: '이미지 다운로드',
    close: '닫기',
    downloading: '다운로드 중...'
  },
  agentEditor: {
    builtinHint: '내장 에이전트입니다. 이름과 설명은 수정할 수 없지만, 설정 매개변수는 조정할 수 있습니다.',
    fileTypes: {
      label: '지원 파일 유형',
      desc: '선택 가능한 파일 유형을 제한합니다. 비워두면 모든 유형을 지원합니다.',
      allTypes: '전체 유형',
      pdf: 'PDF 문서',
      word: 'Word 문서 (.docx/.doc)',
      textLabel: '텍스트',
      text: '일반 텍스트 파일 (.txt)',
      markdown: 'Markdown 문서',
      csv: '쉼표로 구분된 값 파일',
      excel: 'Excel 스프레드시트 (.xlsx/.xls)',
      imageLabel: '이미지',
      image: '이미지 파일 (.jpg/.jpeg/.png)'
    },
    fallback: {
      fixed: '고정 응답',
      model: '모델 생성'
    },
    faq: {
      title: 'FAQ 우선 전략'
    },
    chatParser: {
      label: '채팅 첨부 파싱 정책',
      desc: '현재 에이전트의 채팅 첨부 파일 유형별 파서 엔진을 지정합니다.',
      waitTimeoutLabel: '첨부 파싱 대기 시간(초)',
      waitTimeoutDesc: '한 번의 답변에서 파싱 중인 첨부를 기다리는 최대 시간이며, 초과하면 미완료 첨부는 건너뜁니다. 대용량/스캔 파일은 늘리세요. 0은 전역 기본값을 사용합니다.'
    },
    audioUpload: {
      label: '음성 업로드',
      desc: '활성화하면 사용자가 대화에서 오디오 파일을 업로드할 수 있으며, ASR 모델로 자동 변환됩니다',
      asrModel: 'ASR 모델',
      asrModelDesc: '음성 인식 모델입니다. 설정하지 않으면 오디오 파일이 플레이스홀더로 전달됩니다',
      asrModelPlaceholder: 'ASR 모델 선택'
    },
    imageUpload: {
      navLabel: '첨부 업로드',
      sectionTitle: '첨부 업로드',
      sectionDesc: '채팅에서 이미지, 문서, 오디오 등 첨부 업로드·파싱 및 관련 모델을 설정합니다',
      label: '이미지 업로드',
      desc: '활성화하면 사용자가 대화에서 이미지를 업로드하고 VLM으로 이해할 수 있습니다',
      vlmModel: 'VLM 모델',
      vlmModelDesc: '이미지 분석을 위한 비전 언어 모델',
      vlmModelPlaceholder: 'VLM 모델을 선택하세요',
      vlmModelRequired: '이미지 업로드 활성화 시 VLM 모델을 선택해야 합니다',
      imageUnderstandingLabel: '첨부 이미지 이해 / 스캔 문서 OCR',
      imageUnderstandingDesc: '이미지로만 구성된 PDF/PPT(스캔 문서)에서 텍스트를 추출할 수 없을 때 VLM OCR을 실행합니다. 파싱 시간이 늘어나며 기본값은 꺼짐입니다.',
      ocrMaxPagesLabel: '스캔 문서 OCR 최대 페이지 수',
      ocrMaxPagesDesc: 'VLM OCR에 전달하는 스캔 문서의 최대 페이지 수입니다. 페이지가 많을수록 범위는 넓어지지만 느리고 비용이 큽니다. 0은 전역 기본값을 사용합니다.',
      useGlobalDefault: '0 = 전역 기본값',
      storageProvider: '이미지 저장소',
      storageProviderDesc: '업로드 이미지의 저장 엔진을 선택합니다. 비워두면 시스템 기본값을 사용합니다',
      storageProviderPlaceholder: '저장 엔진 선택',
      storageDefault: '시스템 기본값',
      notConfigured: '미설정',
      goStorageSettings: '저장소 설정으로 이동'
    },
    llmCallTimeout: {
      label: 'LLM 호출 타임아웃',
      desc: '모델 클라이언트의 요청 타임아웃 설정(초)입니다. 출력이 계속되는 스트리밍 응답은 전체 시간이 이 값을 초과할 수 있습니다.',
      hint: '비워두거나 0이면 기본값(120초)을 사용합니다',
      placeholder: '초 단위로 입력하세요. 권장 범위 60-1800'
    },
    mcp: {
      label: 'MCP 서비스',
      desc: 'Agent가 호출할 수 있는 MCP 서비스를 선택하세요',
      selectLabel: 'MCP 서비스 선택',
      selectDesc: '활성화할 MCP 서비스를 선택하세요',
      selectPlaceholder: 'MCP 서비스 선택',
      authWaitTimeout: '인증 대기 시간(초)',
      authWaitTimeoutDesc: '대화 중 OAuth 인증이 필요할 때 인증 완료를 기다리는 최대 시간(초)이며, 초과하면 인증 요청을 건너뜁니다(OAuth를 사용하는 MCP 서비스에만 적용).',
      authWaitTimeoutPlaceholder: '기본 600초',
      accessLevel: '실행 권한 상한',
      accessLevelDesc: '데이터를 변경하는 도구(MCP 도구, Wiki 쓰기)를 확인 없이 실행할지 여부입니다. 읽기 전용이면 이러한 도구를 제공하지 않고, 변경 전 확인이면 매번 확인을 요청합니다. 승인이 필요하도록 표시된 MCP 도구는 항상 확인합니다.',
      unavailableService: '사용할 수 없는 서비스'
    },
    agentType: {
      label: '에이전트 유형',
      desc: '프리셋을 선택하면 시스템 프롬프트, 도구 목록, 권장 지식 베이스 범위가 자동으로 채워집니다.',
      defaultNamePattern: '나의 {label}',
      kbIncompatibleWarn: '선택된 {count}개의 지식 베이스가 현재 유형과 호환되지 않습니다. 수동으로 조정해 주세요.',
      kbMismatch: {
        ragQa: 'RAG 검색 비활성화',
        wikiQa: 'Wiki 비활성화',
        hybridRagWiki: '활성화된 검색 수단 없음',
        dataAnalysis: 'RAG 필요 (FAQ 미지원)',
        quickAnswer: '빠른 답변 모드는 RAG 검색이 필요합니다',
        generic: '현재 유형과 호환 안 됨'
      }
    },
    im: {
      title: 'IM 통합',
      description: '에이전트를 Feishu, Slack, Telegram, DingTalk, Mattermost, QQBot, Yunzhijia 등 인스턴트 메시징 플랫폼에 연결',
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
      addChannel: '채널 추가',
      channelsTitle: 'IM 채널',
      disabled: '비활성',
      editChannel: '채널 편집',
      deleteConfirm: '이 채널을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.',
      channelName: '채널 이름',
      channelNamePlaceholder: '식별하기 쉬운 이름을 입력하세요',
      channelNameDefaultHint: '기본값은 플랫폼 이름이며, 직접 수정할 수 있습니다. 비워 두면 저장 시 플랫폼 이름이 사용됩니다',
      platform: '플랫폼',
      mode: '연결 모드',
      outputMode: '출력 모드',
      outputStream: '스트리밍',
      outputFull: '전체 응답',
      callbackUrl: '콜백 URL',
      empty: 'IM 채널이 없습니다',
      unnamed: '이름 없는 채널',
      docLink: '통합 가이드 보기',
      wecomConsole: 'WeCom 관리 콘솔',
      feishuConsole: 'Feishu 개발 플랫폼',
      larkConsole: 'Lark 개발 플랫폼',
      slackConsole: 'Slack API 콘솔',
      telegramConsole: 'Telegram BotFather',
      dingtalkConsole: 'DingTalk 개발 플랫폼',
      dingtalkCardTemplateId: '카드 템플릿 ID (선택 사항)',
      dingtalkCardTemplateIdHint: 'open-dev.dingtalk.com/fe/card에서 AI 카드 템플릿을 만들면 타자기 효과 스트리밍 출력이 활성화됩니다',
      mattermostConsole: 'Mattermost 통합',
      qqbotConsole: 'QQ Open Platform',
      qqbotAPIBaseURLHint: '선택 사항. 비워두면 기본 프로덕션 API 엔드포인트를 사용합니다.',
      qqbotGatewayURLHint: '선택 사항. 비워두면 공용 WebSocket gateway를 자동으로 가져옵니다.',
      yunzhijiaConsole: 'Yunzhijia Open Platform',
      yunzhijiaRobotDoc: '로봇 메시지 문서',
      yunzhijiaImageDoc: '개발자 플랫폼 (이미지)',
      yunzhijiaModeHint: 'Webhook과 WebSocket을 지원하며 WebSocket 모드에는 공개 콜백 URL이 필요하지 않습니다.',
      yunzhijiaSendMsgUrl: '메시지 전송 URL',
      yunzhijiaSendMsgUrlHint: '로봇 응답 전송에 사용됩니다.',
      yunzhijiaSecret: '서명 시크릿 (선택 사항)',
      yunzhijiaSecretPlaceholder: 'Yunzhijia 로봇 설정의 HmacSHA1 서명 시크릿',
      yunzhijiaSecretHint: '설정하면 들어오는 콜백 요청이 HmacSHA1 서명으로 검증됩니다',
      yunzhijiaAppId: 'App ID (이미지 다운로드)',
      yunzhijiaAppIdPlaceholder: 'Yunzhijia Open Platform App ID',
      yunzhijiaAppSecret: 'App Secret (이미지 다운로드)',
      yunzhijiaAppSecretPlaceholder: 'Yunzhijia Open Platform App Secret',
      yunzhijiaAppCredentialHint: '사용자가 보낸 이미지를 다운로드하기 위한 appAccessToken 발급에 사용됩니다.',
      yunzhijiaTimeout: 'HTTP 타임아웃 (초)',
      yunzhijiaTimeoutHint: '메시지 전송 URL을 통한 응답 전송 타임아웃, 기본 10초',
      yunzhijiaAllowedHostSuffix: '허용 호스트 접미사',
      yunzhijiaAllowedHostSuffixHint: '보안을 위해 메시지 전송 URL 호스트를 이 접미사로 제한 (예: yunzhijia.com)',
      yunzhijiaSendMsgUrlRequired: 'Yunzhijia 로봇 설정의 메시지 전송 URL을 입력하세요',
      mattermostModeHint: 'Mattermost는 Webhook(아웃고잉 웹훅 + 봇 토큰)만 지원합니다.',
      mattermostPostToMain: '답변을 채널 메인 타임라인에 표시',
      mattermostPostToMainHint: '켜면 봇 답변이 채널의 새 최상위 게시물로 올라갑니다. 끄면(기본) 스레드 답변이며 메인 화면에는 「N개 답변」만 보입니다.',
      modeHint: 'WebSocket 방식이 설정이 더 간편하여 권장됩니다',
      consoleTip: '자격 증명 정보를 가져오세요',
      wecomWSEndpointHint: '선택 사항. 프라이빗 WeCom 배포 시 사용자 정의 WebSocket 주소를 입력하세요. 비워두면 기본 퍼블릭 클라우드 주소를 사용합니다. 내부 네트워크 주소의 경우 SSRF_WHITELIST 환경 변수에 호스트명을 추가하세요.',
      wecomAPIBaseURLHint: '선택 사항. 프라이빗 WeCom 배포 시 사용자 정의 API 기본 URL을 입력하세요. 비워두면 기본 퍼블릭 클라우드 주소를 사용합니다. 내부 네트워크 주소의 경우 SSRF_WHITELIST 환경 변수에 호스트명을 추가하세요.',
      feishuAPIBaseURLHint: '선택 사항. 서버가 외부 인터넷에 직접 연결 가능하면 비워두세요. 프록시를 통해서만 접근 가능한 경우 역방향 프록시 URL(예: nginx, http://host:port)을 입력하세요. 내부 네트워크 주소는 SSRF_WHITELIST 환경 변수에 호스트명을 추가하세요.',
      fileKnowledgeBase: '파일 저장 지식 베이스',
      fileKnowledgeBasePlaceholder: '지식 베이스 선택 (선택 사항)',
      fileKnowledgeBaseHint: '설정 시 사용자가 보낸 파일이 자동으로 해당 지식 베이스에 저장됩니다',
      sessionMode: '세션 모드',
      sessionModeUser: '사용자별 (기본)',
      sessionModeThread: '스레드별',
      sessionModeHint: '사용자 모드: 각 사용자별 독립 대화. /clear로 새 대화 시작. 스레드 모드: 메시지 스레드별 독립 대화. 같은 스레드에서 여러 명이 함께 대화 가능.',
      replyLanguage: '응답 언어',
      replyLanguageDefault: '시스템 기본값 사용',
      replyLanguageHint: '이 채널의 에이전트 응답 언어를 고정합니다. 설정하지 않으면 배포 기본 언어를 사용합니다.',
      wechatScanBind: 'QR 코드를 스캔하여 WeChat 연결',
      wechatScanning: 'WeChat으로 QR 코드를 스캔하세요',
      wechatBindSuccess: 'WeChat이 연결되었습니다',
      wechatRebind: '다시 연결',
      wechatHint: 'iOS WeChat 8.0.70+ 버전이 필요하며, 1:1 채팅 메시지만 지원됩니다',
      wechatQRExpired: 'QR 코드가 만료되었습니다. 다시 가져오세요',
      wechatBinding: '연결 중...',
      sectionChannel: '채널 정보',
      sectionConnection: '연결 설정',
      sectionCredentials: '플랫폼 자격 증명',
      selectPlatform: '플랫폼 선택',
      selectPlatformDesc: '연결할 메시징 플랫폼을 선택하세요',
      enabled: '채널 활성화',
      stepBasic: '기본 정보',
      stepConnection: '연결 설정',
      stepKnowledge: '파일 저장',
      stepCredentials: '플랫폼 자격 증명',
      sectionAccess: '접속 및 출력',
      sectionSession: '세션 설정',
      sectionCallback: '콜백 URL',
      sectionKnowledge: '파일 저장',
      sectionStatus: '실행 상태'
    },
    embed: {
      title: '웹 페이지 임베드'
    },
    tools: {
      thinking: '사고',
      thinkingDesc: '동적이고 반성적인 문제 해결 사고 도구',
      todoWrite: '계획 수립',
      todoWriteDesc: '구조화된 연구 계획 생성',
      askUser: '사용자에게 질문',
      askUserDesc: '필요한 정보가 부족할 때 사용자에게 질문하고 답변을 기다린 후 계속합니다',
      searchKnowledge: '지식베이스 검색',
      searchKnowledgeDesc: '의미, 키워드 또는 하이브리드 방식으로 지식베이스 청크 검색',
      readDocument: '문서 읽기',
      readDocumentDesc: '문서 메타데이터와 청크 내용을 읽으며 페이징과 문서 내 검색 지원',
      listDocuments: '문서 목록 보기',
      listDocumentsDesc: '지식베이스의 문서를 페이지 단위로 나열',
      queryGraph: '지식 그래프 쿼리',
      queryGraphDesc: '지식 그래프에서 관계 조회',
      dbQuery: '데이터베이스 쿼리',
      dbQueryDesc: '데이터베이스에서 정보 조회',
      dataAnalysis: '데이터 분석',
      dataAnalysisDesc: '데이터 파일을 이해하고 데이터 분석 수행',
      dataSchema: '데이터 스키마 보기',
      dataSchemaDesc: '테이블 파일의 메타 정보 조회',
      requiresKb: '(지식베이스 설정 필요)',
      requiresRagKb: '(벡터/키워드 인덱싱이 활성화된 지식베이스가 필요합니다)',
      requiresWikiKb: '(Wiki 기능이 활성화된 지식베이스가 필요합니다)',
      wikiSearch: 'Wiki 검색',
      wikiSearchDesc: 'Wiki 지식베이스에서 키워드/의미 기반 검색',
      wikiReadPage: 'Wiki 페이지 읽기',
      wikiReadPageDesc: '지정한 Wiki 페이지의 전체 내용을 읽습니다',
      wikiFlagIssue: 'Wiki 문제 표시',
      wikiFlagIssueDesc: '사실 오류나 병합 충돌을 표시합니다',
      wikiWritePage: 'Wiki 생성/덮어쓰기',
      wikiWritePageDesc: '새 페이지 생성 또는 기존 페이지 완전 덮어쓰기',
      wikiReplaceText: 'Wiki 텍스트 교체',
      wikiReplaceTextDesc: 'Wiki 페이지의 특정 텍스트 교체',
      wikiRenamePage: 'Wiki 이름 변경',
      wikiRenamePageDesc: 'Wiki 페이지 이름을 변경하고 연결된 링크를 자동 갱신',
      wikiDeletePage: 'Wiki 삭제',
      wikiDeletePageDesc: 'Wiki 페이지를 삭제하고 끊어진 링크를 자동 정리',
      wikiReadIssue: 'Wiki 문제 보기',
      wikiReadIssueDesc: '특정 Wiki 페이지 문제의 상세 조회',
      wikiUpdateIssue: 'Wiki 문제 업데이트',
      wikiUpdateIssueDesc: 'Wiki 페이지 문제의 처리 상태 업데이트',
      webSearch: '웹 검색',
      webFetch: '웹 페이지 가져오기',
      groupBase: '기본',
      groupRag: '지식베이스 검색 (RAG)',
      groupWikiRead: 'Wiki 읽기',
      groupWikiEdit: 'Wiki 편집',
      groupWikiIssue: 'Wiki 점검',
      groupData: '데이터 분석',
      writeWarning: 'Wiki 내용을 변경합니다',
      dangerTag: '쓰기',
      statusNoKb: '연결된 지식베이스가 없습니다',
      kbMetricRag: 'RAG 지식베이스',
      kbMetricWiki: 'Wiki 지식베이스',
      statusInactive: '{count}개의 체크된 도구가 현재 설정에서는 작동하지 않습니다',
      searchConversations: '이전 대화 검색',
      searchConversationsDesc: '사용자 본인의 이전 대화에서 나눴던 내용을 찾습니다',
      groupStored: '저장되었지만 여기서 제공하지 않는 도구',
      switchManagedDesc: '이 목록이 아니라 에이전트의 다른 설정으로 제어되는 도구라, 여기서 체크해도 켜지지 않습니다. 체크를 해제하면 삭제됩니다.',
      unrecognizedDesc: '이 버전에 없는 도구라 에이전트가 호출할 수 없습니다. 체크를 해제하면 삭제됩니다.',
      keptUnknownWarning: '저장했습니다. 다음 도구는 이 버전에 없어 그대로 남겨 두었지만, 에이전트가 호출할 수 없습니다: {names}',
      droppedWarning: '저장했습니다. 다음 도구는 에이전트의 다른 설정으로 제어되므로 도구 목록에서 뺐습니다: {names}',
      effectiveLabel: '최종 활성 도구',
      effectiveDesc: '현재 설정 기준 저장 시 에이전트가 실제 호출할 수 있는 도구 집합',
      effectiveEmpty: '사용 가능한 도구가 없어 일반 모델 대화로 동작합니다'
    },
    desc: {
      name: '에이전트를 쉽게 식별할 수 있는 이름을 설정하세요',
      description: '에이전트의 용도와 특징을 간단히 설명하세요',
      systemPrompt: '에이전트의 동작과 역할을 정의하는 사용자 정의 시스템 프롬프트',
      promptInheritance: '템플릿 원문은 업데이트를 따르며, 수정한 내용은 사용자 지정 프롬프트로 저장됩니다. 에이전트 모드에서 역할과 작업 요구사항을 정의하며, 도구 권한과 각 요청의 소스 선택은 별도로 제어됩니다.',
      useCustomSystemPrompt: '기본 페르소나 교체',
      useCustomSystemPromptDesc: '켜면 이 프롬프트가 플랫폼 기본 페르소나를 대체합니다. 도구 사용 및 인용 규약은 여전히 플랫폼이 주입합니다. 끄면 기본 페르소나 뒤에 추가 지시로 붙습니다.',
      leaveEmptyDefault: '(비워두면 시스템 기본값 사용)',
      contextTemplate: '검색된 콘텐츠를 모델에 전달하기 전에 형식을 정의합니다',
      model: '에이전트가 사용할 대규모 언어 모델을 선택하세요',
      temperature: '출력의 무작위성을 제어합니다. 0이 가장 확정적, 1이 가장 무작위',
      maxTokens: '모델 응답의 최대 토큰 수. 「기본값」은 2048입니다. 「사용자 지정」은 입력한 값을 그대로 저장합니다.',
      maxTokensAgent: '각 추론 라운드에서 생성할 최대 토큰 수(도구 호출 JSON 포함). 기본값은 24576입니다. 사용자 지정 값은 입력한 대로 저장됩니다.',
      thinking: '모델의 확장 사고 기능 활성화 (모델 지원 필요)',
      queryUnderstandModel: '질문 이해(재작성과 의도 분류)에 사용할 모델입니다. 비워 두면 기본 대화 모델을 사용합니다.',
      rewriteSystemPrompt: '질문 재작성용 시스템 프롬프트 (비워두면 기본값 사용)',
      rewriteUserPrompt: '질문 재작성용 사용자 프롬프트 템플릿 (비워두면 기본값 사용)',
      selectTools: 'Agent가 사용할 수 있는 도구를 선택하세요',
      maxIterations: '주 에이전트가 한 턴에 모델을 호출하는 횟수를 제한합니다.',
      kbScope: '에이전트가 접근할 수 있는 지식베이스 범위를 선택하세요',
      fallbackStrategy: '지식베이스에서 관련 콘텐츠를 찾을 수 없을 때 처리 방식',
      fallbackResponse: '응답할 수 없을 때 반환할 고정 텍스트',
      fallbackPrompt: '지식베이스에서 답변을 찾을 수 없을 때 모델 응답을 유도하는 프롬프트',
      memoryEnabled: '이 에이전트가 장기 기억을 읽고 추가하도록 허용합니다. 끄면 이 에이전트와의 대화에서 기억을 읽지도, 새로 추가하지도 않습니다. 공간 또는 개인 설정이 꺼져 있으면 여기서 켜도 적용되지 않습니다'
    },
    selection: {
      all: '전체',
      selected: '지정',
      disabled: '비활성화'
    },
    promptNav: {
      ariaLabel: '프롬프트 목차',
      system: '시스템 프롬프트',
      context: '컨텍스트 템플릿',
      intent: '의도 프롬프트',
      rewriteSystem: '재작성 · 시스템',
      rewriteUser: '재작성 · 사용자',
      fallback: '검색 폴백'
    },
    intentPrompts: {
      title: '의도 프롬프트',
      sectionDesc: '쿼리 의도별 시스템 프롬프트를 설정합니다. 사용자 정의가 없으면 기본 템플릿이 적용됩니다',
      intentLabel: '의도',
      promptPlaceholder: '사용자 정의 시스템 프롬프트 입력...',
      customized: '사용자 정의됨',
      empty: '사용 가능한 의도 템플릿이 없습니다'
    },
    placeholders: {
      available: '사용 가능한 변수: ',
      clickToInsert: '(클릭하여 삽입)',
      hint: '(클릭하여 삽입, 또는 {\'{{\'} 입력으로 목록 표시)'
    },
    questionSuggestions: {
      title: '대화 질문 추천'
    },
    navGroups: {
      basic: '기본',
      knowledge: '지식 검색',
      capability: '기능 확장'
    }
  },
  agentStream: {
    saveToKb: {
      emptyContent: '현재 응답이 비어 있어 지식베이스에 저장할 수 없습니다',
      editorOpened: '편집기가 열렸습니다. 지식베이스를 선택한 후 저장하세요'
    },
    copy: {
      emptyContent: '현재 응답이 비어 있어 복사할 수 없습니다',
      success: '클립보드에 복사되었습니다',
      failed: '복사 실패, 수동으로 복사하세요'
    },
    toolStatus: {
      calling: '{name} 호출 중...',
      searchKb: '지식베이스 검색',
      searchKbFailed: '지식베이스 검색 실패',
      searchMixed: '지식베이스 및 웹 검색',
      searchMixedFailed: '검색 실패',
      webSearch: '웹 검색',
      webSearchFailed: '웹 검색 실패',
      grepSearch: '키워드 검색',
      grepSearchFailed: '키워드 검색 실패',
      getDocInfo: '문서 정보 조회',
      getDocInfoFailed: '문서 정보 조회 실패',
      viewDocument: 'View document',
      thinkingDone: '사고 완료',
      thinkingFailed: '사고 실패',
      updateTodos: '작업 목록 업데이트',
      updateTodosFailed: '작업 목록 업데이트 실패',
      imageAnalyzing: '이미지 내용 분석 중...',
      imageAnalysisDone: '이미지 내용 분석 완료',
      imageAnalysisFailed: '이미지 내용 분석 실패',
      attachmentParsing: '첨부 파일 파싱 중...',
      attachmentParsingDone: '첨부 파일 파싱 완료',
      attachmentParsingFailed: '첨부 파일 파싱 실패',
      queryUnderstanding: '질문 이해 중...',
      queryUnderstandDone: '질문 이해 완료',
      called: '{name} 호출 완료',
      calledFailed: '{name} 호출 실패',
      shellExecRunning: '샌드박스 명령 실행 중...'
    },
    mcp: {
      discoverTools: 'MCP 도구 탐색',
      listServers: 'MCP 서비스 목록',
      listTools: 'MCP 도구 목록',
      searchTools: 'MCP 도구 검색',
      describeTool: '도구 정의 읽기',
      callTool: 'MCP 도구 호출',
      showing: '{total}개 중 {count}개 표시',
      moreAvailable: '결과가 더 있습니다',
      empty: '표시할 항목이 없습니다',
      parameters: '매개변수',
      expand: '설명 펼치기',
      collapse: '접기',
      required: '필수',
      fullSchema: '전체 매개변수 정의',
      failed: 'MCP 작업 실패',
      result: '실행 결과'
    },
    ragPipeline: {
      searching: '지식베이스 검색 중...',
      searchingWithQuery: '지식베이스 검색 중: 「{query}」',
      searchingWeb: '웹 검색 중...',
      searchingWebWithQuery: '웹 검색 중: 「{query}」',
      searchingMixed: '지식베이스 및 웹 검색 중...',
      searchingMixedWithQuery: '지식베이스 및 웹 검색 중: 「{query}」',
      searchDone: '검색 완료'
    },
    attachmentParsing: {
      parsedSummary: '첨부 파일 {count}개 파싱 완료',
      parsedWithSkipped: '첨부 파일 {parsed}개 파싱 완료, {skipped}개 미완료로 건너뜀',
      noneReady: '사용 가능한 파싱된 첨부 파일이 없습니다'
    },
    knowledgeChunksList: {
      chunkRange: '{fetched} / {total} 청크 로드됨',
      page: '{page}페이지, 페이지당 {pageSize}개',
      offsetRange: '청크 {from}–{to}',
      queryMatches: '문서 내 검색 "{query}": {count}건 일치',
      queryNoMatch: '문서 내 검색 "{query}": 일치 없음'
    },
    grepResults: {
      chunkHits: '청크 {count}개',
      keywordHits: '{count}회',
      titleMatch: '제목',
      faqEntry: 'FAQ entry'
    },
    search: {
      noResults: '일치하는 내용을 찾을 수 없습니다',
      candidatesBelowThreshold: '후보 {count}개를 찾았지만 관련성이 부족해 답변에 사용하지 않았습니다',
      foundResultsFromFiles: '{files}개 파일에서 {count}개 결과 발견',
      foundResults: '{count}개 결과 발견',
      foundMixedResults: '{count}개 결과 발견 ({docCount}개 문서, {webCount}개 웹)',
      webResults: '웹 결과 {count}개 발견',
      grepSummary: '일치하는 청크 {chunks}개, 문서 {docs}개'
    },
    plan: {
      inProgress: '진행 중',
      pending: '대기 중',
      completed: '완료'
    },
    toolSummary: {
      getDocument: '문서 조회: {title}',
      document: '문서',
      listChunks: '보기 {title}',
      listFaqEntry: 'View FAQ: {question}',
      deepThinking: '깊은 사고'
    },
    entityLink: {
      kb: '지식베이스',
      doc: '문서',
      chunk: '청크'
    },
    citation: {
      notFound: '콘텐츠를 찾을 수 없습니다',
      loadFailed: '로드 실패',
      noKbForWiki: '연결된 지식베이스를 식별할 수 없어 Wiki를 열 수 없습니다'
    },
    weknoraDocs: {
      pages: '문서 {count}편',
      hits: '일치하는 섹션 {count}개',
      empty: '일치하는 문서가 없습니다',
      outline: '목차',
      content: '본문',
      truncated: '본문이 이어집니다',
      failed: '읽기 실패',
      openDoc: '문서 사이트에서 열기'
    },
    operations: {
      found: '실행 가능 {count}개',
      unavailableCount: '현재 사용 불가 {count}개',
      empty: '일치하는 작업이 없습니다',
      unavailableHeading: '현재 사용 불가',
      parameters: '매개변수',
      required: '필수',
      enum: '허용 값',
      range: '범위 {min}–{max}',
      truncated: '결과가 잘렸습니다',
      emptyResult: '반환된 데이터가 없습니다',
      failed: '작업 실패',
      meta: '추가 정보',
      risk: {
        read: '읽기',
        probe: '점검',
        write: '쓰기',
        destructive: '되돌릴 수 없음'
      },
      names: {
        session: {
          list: '대화 목록 조회'
        },
        automation: {
          list: '자동화 목록 가져오기',
          create: '자동화 만들기',
          validate_trigger: '실행 시간 확인',
          get: '자동화 상세 가져오기',
          update: '자동화 수정',
          delete: '자동화 삭제',
          pause: '자동화 일시 중지',
          resume: '자동화 다시 시작',
          run_now: '자동화 즉시 실행',
          list_runs: '자동화 실행 기록 가져오기'
        },
        skill: {
          list_installed: '설치된 스킬 목록 조회',
          install: '스킬 설치',
          get_installed: '설치된 스킬 상세 조회',
          uninstall: '스킬 제거',
          set_enabled: '스킬 활성화 상태 설정',
          list: '실행 가능한 스킬 목록 조회',
          list_catalog: '워크스페이스 스킬 목록 조회',
          get_catalog: '워크스페이스 스킬 상세 조회',
          install_catalog: '카탈로그 스킬을 샌드박스에 설치'
        },
        model: {
          list: '모델 목록 조회',
          list_providers: '모델 제공업체 목록 조회',
          get_provider: '모델 제공업체 상세 조회',
          get: '모델 상세 조회',
          delete: '모델 삭제',
          update: '모델 표시 정보 수정',
          copy: '모델 설정 복사'
        },
        message: {
          chat_history_stats: '채팅 기록 통계 조회',
          search: '대화 기록 검색',
          list: '메시지 기록 조회'
        },
        mcp_service: {
          list: 'MCP 서비스 목록 조회',
          create: 'MCP 서비스 생성',
          get: 'MCP 서비스 상세 조회',
          update: 'MCP 서비스 수정',
          delete: 'MCP 서비스 삭제',
          test: 'MCP 서비스 연결 테스트',
          list_tools: 'MCP 도구 실시간 조회',
          get_metadata: '동기화된 MCP 도구 보기',
          refresh_metadata: 'MCP 도구 목록 동기화'
        },
        web_search_provider: {
          list: '웹 검색 서비스 목록 조회',
          get: '웹 검색 서비스 상세 조회',
          list_types: '웹 검색 서비스 유형 조회',
          test: '웹 검색 연결 테스트',
          update: '웹 검색 서비스 수정',
          delete: '웹 검색 서비스 삭제'
        },
        system: {
          get_info: '버전 및 시스템 정보 조회'
        },
        workspace: {
          get: '현재 워크스페이스 정보 조회',
          update: '현재 워크스페이스 기본 정보 수정',
          list_members: '현재 워크스페이스 구성원 조회'
        },
        system_admin: {
          list_admins: '시스템 관리자 조회',
          list_users: '플랫폼 사용자 조회',
          list_settings: '시스템 설정 조회',
          get_queues: '작업 큐 실행 상태 조회',
          list_tasks: '큐 작업 조회'
        },
        wiki: {
          list_folders: 'Wiki 폴더 목록 조회',
          create_folder: 'Wiki 폴더 생성',
          list_issues: 'Wiki 페이지 문제 목록 조회',
          lint: 'Wiki 페이지 검사',
          move_page: 'Wiki 페이지 이동',
          get_page: 'Wiki 페이지 조회',
          rebuild_links: 'Wiki 링크 재구축',
          revert: 'Wiki 페이지 버전 복원',
          list_revisions: 'Wiki 페이지 버전 목록 조회',
          get_stats: 'Wiki 통계 조회'
        },
        knowledge: {
          list: '지식 목록 조회',
          list_folders: '지식 폴더 목록 조회',
          rename_folder: '폴더 이름 변경 또는 이동',
          create_manual: '지식 수동 생성',
          create_from_url: 'URL에서 지식 생성',
          batch_delete: '지식 일괄 삭제',
          batch_reparse: '지식 일괄 재분석',
          move_to_folder: '지식을 폴더로 이동',
          update_manual: '수동 생성 지식 수정',
          move: '지식을 다른 지식 베이스로 이동',
          get_move_progress: '지식 이동 진행 상황 조회',
          set_tags: '지식 태그 설정',
          get: '지식 상세 조회',
          update: '지식 수정',
          delete: '지식 삭제',
          cancel_parse: '지식 분석 취소',
          reparse: '지식 재분석',
          get_parse_progress: '지식 분석 진행 상황 조회'
        },
        faq: {
          batch_update: 'FAQ 상태 및 태그 일괄 수정',
          list_entries: 'FAQ 항목 목록 조회',
          delete_entries: 'FAQ 항목 일괄 삭제',
          get_entry: 'FAQ 항목 상세 조회',
          update_entry: 'FAQ 항목 수정',
          add_similar_questions: '유사 질문 추가',
          create_entry: 'FAQ 항목 생성'
        },
        knowledge_base: {
          list_parser_engines: '사용 가능한 파싱 엔진 조회',
          copy: '지식베이스 내용 복사',
          duplicate: '지식베이스 설정 복사',
          get_copy_progress: '지식베이스 복사 진행 상황 조회',
          list: '지식 베이스 목록 조회',
          create: '지식 베이스 생성',
          get: '지식 베이스 상세 조회',
          delete: '지식 베이스 삭제',
          update: '지식 베이스 수정',
          list_activity: '지식 베이스 활동 조회',
          search: '지식 베이스 검색',
          list_move_targets: '이동 대상 지식 베이스 조회',
          generate_profile: '지식 베이스 설명 생성',
          list_tags: '지식 베이스 태그 목록 조회',
          create_tag: '지식 베이스 태그 생성',
          update_tag: '지식 베이스 태그 수정',
          delete_tag: '지식 베이스 태그 삭제',
          list_shared: '공유 지식 베이스 목록 조회'
        },
        chunk: {
          get: '청크 상세 조회',
          update: '청크 수정',
          list_revisions: '청크 변경 이력 조회',
          revert: '청크 이전 버전 복원',
          list: '지식 청크 목록 조회'
        },
        artifact: {
          list: '생성 파일 목록 조회'
        },
        agent: {
          list: '에이전트 목록 조회',
          create: '에이전트 생성',
          get: '에이전트 상세 조회',
          delete: '에이전트 삭제',
          update: '에이전트 수정',
          copy: '에이전트 복사'
        },
        data_source: {
          list: '데이터 소스 목록 조회',
          get: '데이터 소스 상세 조회',
          test: '데이터 소스 연결 테스트',
          sync: '데이터 소스 동기화',
          pause: '데이터 소스 동기화 일시 중지',
          resume: '데이터 소스 동기화 재개',
          list_sync_logs: '데이터 소스 동기화 이력 조회',
          get_sync_log: '데이터 소스 동기화 진행 상황 조회',
          list_resources: '동기화 가능한 리소스 조회',
          update_sync: '데이터 소스 동기화 설정 수정'
        }
      }
    },
    shellExec: {
      workDir: '디렉터리',
      exitCode: '종료 코드',
      stdout: '표준 출력',
      stderr: '표준 에러',
      emptyOutput: '출력 없음',
      truncated: '출력이 잘림',
      killed: '시간 초과로 종료됨',
      binarySuppressed: '바이너리 출력은 생략되었습니다. 파일은 산출물 디렉터리에 저장한 뒤 다운로드하세요.'
    },
    sandboxFiles: {
      found: '파일 {count}개 발견',
      empty: '파일 없음',
      truncated: '목록이 잘림',
      wrote: '씀',
      replacements: '{count}곳 치환',
      moreLines: '{count}줄 더'
    },
    imageView: {
      summary: '"{file}"의 이미지 {numbers}을(를) 확인했습니다 (총 {total}장)',
      single: '이미지 "{file}"을(를) 확인했습니다',
      descriptionsHeading: '비전 모델의 이미지 설명',
      imageLabel: '이미지 #{n}',
      noDescription: '설명을 생성하지 못했습니다',
      remaining: '확인하지 않은 이미지 {count}장 남음'
    },
    attachmentTarget: {
      list: '모든 첨부 파일',
      file: '첨부 파일',
      images: '{name}의 이미지',
      imagesUnnamed: '첨부 파일 이미지',
      image: '{name}의 이미지 {n}',
      imageUnnamed: '첨부 파일 이미지 {n}'
    },
    skillFiles: {
      heading: '스킬 파일',
      script: '스크립트',
      instructions: '스킬 안내'
    },
    openPage: {
      open: '열기',
      retired: '지원 종료',
      openForm: '열고 입력',
      opened: '어시스턴트가 열었습니다',
      back: '돌아가기',
      endpoint: '연결 대상: ',
      draftHint: '어시스턴트가 미리 채웠습니다. API 키 등 자격 증명을 입력하고 확인한 뒤 직접 저장하세요.'
    },
    pageEdit: {
      title: '{count}곳을 입력했습니다',
      undo: '되돌리기',
      undone: '입력을 되돌렸습니다',
      undoSkipped: '{count}곳은 이미 변경되었거나 페이지에 없어 그대로 두었습니다',
      unsaved: '아직 저장되지 않았습니다. 확인 후 페이지에서 저장하세요.'
    },
    pageAccess: {
      viewed: '현재 페이지를 확인했습니다: {location}'
    },
    collaboration: {
      tabs: '작업 탭',
      updates: '업데이트 {count}개',
      mainConversation: '기본 대화',
      assignment: '작업 내용',
      title: '하위 작업',
      unnamed: '이름 없는 작업',
      phase: {
        tool_running: '도구 사용 중',
        tool_succeeded: '도구 완료',
        tool_failed: '도구 실패'
      },
      status: {
        queued: '대기 중',
        running: '진행 중',
        waiting: '입력 대기 중',
        succeeded: '완료',
        failed: '실패',
        interrupted: '중단됨',
        cancelled: '취소됨',
        needs_attention: '확인 필요',
        cancelling: '취소 중',
        unknown: '알 수 없음'
      }
    },
    tools: {
      searchKnowledge: '지식베이스 검색',
      grepChunks: '텍스트 패턴 검색',
      webSearch: '웹 검색',
      webFetch: '웹 페이지 가져오기',
      getDocumentInfo: '문서 정보 조회',
      listKnowledgeChunks: '지식 청크 목록',
      getRelatedDocuments: '관련 문서 찾기',
      getDocumentContent: '문서 내용 가져오기',
      wikiReadSourceDoc: '원본 문서 읽기',
      readDocument: '문서 읽기',
      listDocuments: '문서 목록 보기',
      todoWrite: '계획 관리',
      askUser: '사용자에게 질문',
      requestSecureForm: '자격 증명 요청',
      browserFillSecret: '자격 증명 입력',
      knowledgeGraphExtract: '지식 그래프 추출',
      thinking: '사고',
      attachmentParsing: '첨부 파일 파싱',
      imageAnalysis: '이미지 내용 분석',
      queryUnderstand: '질문 이해',
      queryKnowledgeGraph: '지식 그래프 조회',
      readSkill: '스킬 읽기',
      executeSkillScript: '스킬 스크립트 실행',
      listSandboxFiles: '샌드박스 파일 목록',
      readFile: '파일 읽기',
      readSandboxFile: '샌드박스 파일 읽기',
      writeSandboxFile: '샌드박스 파일 쓰기',
      editSandboxFile: '샌드박스 파일 편집',
      shellExec: '샌드박스 명령 실행',
      dataAnalysis: '데이터 분석',
      dataSchema: '데이터 구조',
      databaseQuery: '데이터베이스 조회',
      findOperations: '작업 찾기',
      runOperation: '작업 실행',
      spawn_agent: '에이전트 시작',
      list_agents: '에이전트 목록',
      send_message: '메시지 보내기',
      followup_task: '작업 계속',
      interrupt_agent: '에이전트 중단',
      wait_agent: '에이전트 대기',
      openPage: '페이지 열기',
      viewPage: '페이지 확인',
      searchWeKnoraDocs: '제품 문서 검색',
      readWeKnoraDoc: '제품 문서 읽기',
      readPage: '페이지 보기',
      selectTab: '탭 선택',
      fillPage: '페이지 입력'
    },
    mcpOAuth: {
      waiting: '인증 대기 · {target}',
      waitingStatus: '인증 대기',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '계속하려면 {target} 인증이 필요합니다',
      titleWithService: 'OAuth · {service}',
      titleWithTool: 'OAuth · {service} › {tool}',
      desc: '인증을 누르면 새 창에서 로그인합니다. 인증이 완료되면 이 도구 호출이 자동으로 계속됩니다.',
      authorize: '인증하기',
      skip: '건너뛰기',
      countdownShort: '{seconds}초',
      authorizedTag: '인증됨',
      timedOutTag: '인증 시간 초과',
      canceledTag: '취소됨',
      authorizedToast: '인증 성공, 계속 진행 중',
      startFailed: '인증 시작 실패',
      resumeFailed: '실행 재개 실패, 다시 시도하세요',
      skipFailed: '건너뛰기 실패, 다시 시도하세요'
    },
    hostReview: {
      denied: '자동 검토에서 거부됨: {reason}'
    },
    hostApproval: {
      command: '명령',
      grantPath: '접근이 필요한 경로',
      accessWrite: '읽기 및 쓰기',
      accessRead: '읽기 전용',
      firstAttemptRan: '이 명령은 이미 한 번 실행되어 실패했습니다. 승인하면 명령 전체가 다시 실행됩니다',
      snippet: '차단 상세',
      sessionRules: '이 세션에서 허용하면 이 디렉터리의 다음 삭제는 다시 묻지 않습니다(파일 이름은 달라도 됨)',
      reject: '거부',
      approveOnce: '한 번만 허용',
      approveSession: '이 세션에서 허용',
      approvedOnce: '한 번 허용됨',
      approvedSession: '이 세션에서 허용됨',
      rejectedTag: '거부됨',
      submitted: '제출됨',
      submitFailed: '제출 실패',
      userRejected: '사용자가 거부함',
      fileOnly: '이 파일만 허용합니다',
      writeMode: '방식',
      writeModeOverwrite: '덮어쓰기',
      writeModeAppend: '추가',
      writeModeEdit: '편집',
      writeBytes: '{bytes}바이트',
      preview: '내용',
      previewTruncated: '처음 64KB만 표시',
      env: '환경 변수',
      skillName: '스킬',
      stdin: '표준 입력',
      script: '명령이 실행하는 스크립트'
    },
    toolApproval: {
      title: '승인',
      toolDescription: '도구 설명',
      delegatedTask: '위임된 작업',
      waitingStatus: '승인 대기',
      targetWithTool: '{service} › {tool}',
      dockQuestion: '{target} 실행을 허용할까요?',
      operationQuestion: '{action} “{target}”을(를) 허용할까요?',
      operationQuestionNoTarget: '{action}을(를) 허용할까요?',
      operationTarget: '{action} “{target}”',
      characterCount: '{count}자',
      argsLabel: '인수',
      argsModified: '수정됨',
      allowInSession: '이 대화에서 같은 작업은 모두 허용',
      countdownShort: '{seconds}초',
      approve: '승인 후 실행',
      reject: '거부',
      approvedTag: '승인됨',
      rejectedTag: '거부됨',
      parked: '백그라운드에서 대기 중 — 나중에 처리할 수 있습니다',
      parkedUntil: '백그라운드에서 대기 중 — {time} 전에 처리하세요',
      abandonedTag: '포기됨',
      canceledTag: '취소됨',
      invalidJson: '유효한 JSON이 아닙니다',
      submitted: '제출됨',
      submitFailed: '제출 실패',
      userRejected: '사용자 거부',
      value: {
        document: '문서',
        faq: 'FAQ',
        wiki: 'Wiki',
        on: '켜짐',
        off: '꺼짐',
        vector: '벡터',
        keyword: '키워드',
        graph: '그래프',
        quickAnswer: '빠른 답변',
        smartReasoning: '스마트 추론',
        indexSep: ', '
      },
      detail: {
        type: '유형',
        embeddingModel: '임베딩 모델',
        summaryModel: '요약 모델',
        captionModel: '이미지 설명',
        speechModel: '음성 인식',
        storage: '스토리지',
        indexes: '인덱스',
        name: '이름',
        title: '제목',
        status: '상태',
        summary: '설명',
        model: '모델',
        mode: '모드',
        url: '링크',
        from: '출발',
        to: '도착',
        folder: '폴더',
        page: '페이지',
        version: '버전',
        documents: '문서',
        knowledgeBases: '지식베이스',
        mcpServices: 'MCP 서비스',
        skills: '스킬',
        webSearch: '웹 검색',
        multiTurn: '멀티턴',
        transport: '전송 방식',
        authentication: '인증 방식',
        usageInstructions: '사용 안내',
        displayName: '표시 이름',
        enabled: '사용',
        sandbox: '샌드박스',
        sandboxes: '샌드박스',
        systemPrompt: '시스템 프롬프트',
        content: '내용',
        kbScope: '지식베이스 범위',
        mcpScope: 'MCP 범위',
        skillsScope: '스킬 범위'
      },
      grantLapsed: {
        changed: '이전 허용이 더 이상 적용되지 않습니다. 자동화의 Agent 설정, 역할 또는 권한 상한이 변경되었습니다.',
        expired: '이전 허용이 만료되었습니다.',
        idle: '이전 허용이 오랫동안 사용되지 않아 만료되었습니다.'
      }
    },
    promptDock: {
      approvalTitle: '검토가 필요합니다',
      oauthTitle: '인증이 필요합니다',
      secureFormTitle: '자격 증명 입력이 필요합니다',
      waiting: '응답 대기 중',
      handle: '응답하기',
      pager: '{current} / {total}',
      previous: '이전',
      next: '다음',
      collapse: '접기',
      expand: '펼치기'
    },
    secureForm: {
      onlyFillInto: '입력 대상: {domains}에만',
      observedAt: '브라우저 현재 페이지: {origin}',
      originUnknown: '브라우저의 현재 페이지를 확인할 수 없습니다. 로그인할 사이트가 열려 있는지 확인하세요',
      originMismatch: '브라우저의 현재 페이지({origin})가 로그인할 사이트와 다릅니다. 확인한 후 입력하세요',
      originInsecure: '브라우저 페이지가 HTTPS가 아니므로 자격 증명이 입력되지 않습니다',
      savedAccount: '저장된 계정',
      useNew: '새 사용자 이름과 비밀번호 사용',
      username: '사용자 이름',
      password: '비밀번호',
      saveToVault: '보관함에 저장',
      useOnce: '이번만 사용',
      fill: '입력',
      decline: '거절',
      submittedHidden: '제출됨(내용 숨김)',
      declined: '거절함',
      timedOut: '시간 초과',
      canceled: '취소됨',
      submitFailed: '제출 실패',
      savedButClosed: '자격 증명은 보관함에 저장되었지만 이 요청은 이미 종료되었습니다'
    },
    askUser: {
      answerLabel: '내 답변',
      title: '질문이 있습니다',
      selectPlaceholder: '선택하세요',
      textPlaceholder: '답변을 입력하세요',
      otherPlaceholder: '기타(선택)',
      decline: '답변 안 함',
      submit: '제출',
      declinedTag: '답변 거절함',
      submitted: '제출됨',
      answeredTag: '답변함',
      timedOutTag: '시간 내 답변 없음',
      canceledTag: '취소됨',
      unansweredTag: '답변 없음',
      submitFailed: '제출 실패'
    }
  },
  kbSettings: {
    parser: {
      title: '파서 엔진',
      description: '파일 유형별 문서 파서 엔진을 선택합니다. 미구성 파일 유형은 내장 파서를 사용합니다.',
      loading: '로딩 중...',
      noEngineAvailable: '사용 가능한 파서 엔진이 없거나 문서 파싱 서비스가 구성되지 않았습니다.',
      default: '기본',
      goConfig: '구성으로 이동 →',
      noEngine: '사용 가능한 엔진 없음',
      fileTypePdf: 'PDF 문서',
      fileTypeWord: 'Word 문서',
      fileTypePpt: '프레젠테이션',
      fileTypeExcel: 'Excel 스프레드시트',
      xlsxFirstRowAsHeader: '첫 행을 각 행의 열 컨텍스트로 사용',
      fileTypeEbook: '전자책',
      fileTypeWebArchive: '웹 아카이브',
      fileTypeCsv: 'CSV 파일',
      fileTypeText: '일반 텍스트',
      fileTypeJson: 'JSON 파일',
      fileTypeImage: '이미지',
      fileTypeAudiovisual: '오디오',
      engines: {
        opendataloader: {
          name: 'OpenDataLoader',
          desc: 'OpenDataLoader PDF 파서 (레이아웃 분석, Java 11+ 및 opendataloader-pdf 필요)'
        },
        markitdown: {
          name: 'MarkItDown',
          desc: 'Microsoft MarkItDown 변환기 (PDF/Office/HTML 등)'
        },
        paddleocr_vl_cloud: {
          name: 'PaddleOCR-VL Cloud',
          desc: 'PaddleOCR-VL Cloud API'
        },
        paddleocr_vl: {
          name: 'PaddleOCR-VL',
          desc: 'PaddleOCR-VL 자체 호스팅 서비스'
        },
        mineru_cloud: {
          name: 'MinerU Cloud',
          desc: 'MinerU Cloud API'
        },
        mineru: {
          name: 'MinerU',
          desc: 'MinerU 자체 호스팅 서비스'
        },
        anydoc: {
          name: 'anydoc',
          desc: '프로세스 내 오피스 문서 파싱 (외부 서비스 불필요)'
        },
        simple: {
          name: 'Simple',
          desc: '간단한 형식 및 이미지 파싱 (외부 서비스 불필요)'
        },
        builtin: {
          name: '내장',
          desc: 'DocReader 내장 파서 엔진 (docx/pdf/xlsx 등 복잡한 형식)'
        }
      }
    },
    storage: {
      title: '스토리지 엔진',
      selectDescription: '이 지식베이스를 바인딩할 구체적인 스토리지 인스턴스를 선택하세요.',
      defaultTag: '기본',
      instanceLabel: '스토리지 인스턴스',
      instanceDesc: '같은 스토리지 유형에 서로 다른 Endpoint, Bucket 또는 자격 증명을 가진 여러 인스턴스를 구성할 수 있습니다.',
      migrateHint: '이 지식베이스에는 이미 파일이 있어 스토리지 마이그레이션 절차를 통해서만 인스턴스를 변경할 수 있습니다.',
      manageInstances: '스토리지 인스턴스 관리',
      localStorage: '로컬 스토리지',
      loading: '로딩 중...'
    },
    vectorStore: {
      title: '벡터 스토어',
      description: '이 지식베이스가 사용할 벡터 스토어를 선택합니다. 생성 후에는 변경할 수 없습니다. 다른 스토어로 옮기려면 새 KB를 만들고 다시 인덱싱하세요.',
      loading: '벡터 스토어 목록을 불러오는 중...',
      engineLabel: '벡터 스토어',
      engineDesc: '전역 벡터 스토어 설정에서 등록한 스토어를 선택하거나, \'시스템 기본값\'을 유지하면 워크스페이스의 RETRIEVE_DRIVER 엔진을 사용합니다.',
      boundLabel: '바인딩된 벡터 스토어',
      systemDefault: '시스템 기본값',
      immutableHint: '생성 후 변경할 수 없습니다. 다른 스토어로 옮기려면 원하는 스토어에 바인딩된 새 KB를 만들고 다시 인덱싱하세요.',
      immutableEdit: '벡터 스토어 바인딩은 생성 후 변경할 수 없습니다.',
      unavailableHint: '바인딩된 벡터 스토어가 현재 사용할 수 없는 상태입니다. 설정 → 벡터 스토어에서 연결 상태를 확인하세요.',
      goGlobalSettings: '벡터 스토어 설정으로 이동'
    }
  },
  vectorStoreBadge: {
    systemDefault: '시스템 기본값',
    sharedFromOrg: '다른 조직에서 공유됨',
    unknownStore: '알 수 없는 스토어',
    unavailable: '사용 불가'
  },
  tools: {
    multiKbSearch: '크로스 KB 검색',
    searchKnowledge: '지식베이스 검색',
    readDocument: '문서 읽기',
    listDocuments: '문서 목록 보기',
    knowledgeSearch: '지식베이스 검색',
    grepChunks: '텍스트 패턴 검색',
    getChunkDetail: '청크 상세 조회',
    listKnowledgeChunks: '지식 청크 목록',
    listKnowledgeBases: '지식베이스 목록',
    getDocumentInfo: '문서 정보 조회',
    queryKnowledgeGraph: '지식 그래프 쿼리',
    think: '깊이 생각하기',
    todoWrite: '계획 수립'
  },
  commandPalette: {
    placeholder: '지식베이스, 파일, 대화 검색…',
    clearRecent: '지우기',
    retrieval: '검색 설정',
    untitledSession: '제목 없는 대화',
    hotkey: {
      select: '이동',
      enter: '열기',
      cmdNumber: '바로 이동',
      cmdEnter: '대화 시작',
      esc: '닫기'
    },
    empty: {
      noResults: '일치하는 결과 없음',
      askAi: 'AI에게 직접 질문하기',
      adjustRetrieval: '검색 설정 조정'
    },
    quick: {
      newChat: '새 대화',
      knowledgeBases: '지식베이스 열기',
      agents: '에이전트 열기',
      organizations: '공유 공간 열기',
      settings: '설정 열기',
      productTour: '사용 가이드',
      assistant: '{name} 열기'
    },
    match: {
      vector: '벡터',
      keyword: '키워드'
    },
    group: {
      chunks: '지식베이스 파일',
      messages: '대화 메시지',
      kbs: '지식베이스',
      agents: '에이전트',
      sessionsByTitle: '대화（제목별）',
      commands: '명령',
      recent: '최근 검색',
      quickActions: '빠른 작업'
    },
    scope: {
      placeholder: '이 지식베이스에서 검색…',
      remove: '범위 해제 (Backspace)'
    }
  },
  assistant: {
    title: 'Xiaozhi 어시스턴트',
    newConversation: '새 대화',
    history: '대화 기록',
    untitledConversation: '제목 없는 대화',
    historyEmpty: '아직 대화 기록이 없습니다',
    historyFailed: '대화 기록을 불러오지 못했습니다',
    loadMore: '더 불러오기',
    resize: '어시스턴트 너비 조정',
    welcomeTitle: '무엇을 도와드릴까요?',
    agentWelcomeDesc: '이 에이전트의 설정을 확인하고, 모델을 변경하거나 검색할 수 있는 지식 베이스를 확인할 수 있습니다.',
    welcomeDesc: 'Xiaozhi 사용법을 안내하고, 지식과 문서를 정리하며, 에이전트·도구·자동화 설정을 도와드릴 수 있습니다.',
    startFailed: '어시스턴트를 시작하지 못했습니다. 다시 시도해 주세요.',
    chooseAction: '기능을 선택하거나 원하는 작업을 입력하세요.',
    askAboutAnswer: '이 답변에 대해 {name}에게 묻기',
    starters: {
      agentConfig: '이 에이전트의 설정에서 무엇을 개선할 수 있나요?',
      agentModel: '이 에이전트에는 어떤 모델이 더 적합한가요?',
      agentKnowledge: '어떤 지식 베이스를 검색할 수 있나요?',
      wikiIssues: '이 Wiki 페이지에서 보완하거나 확인해야 할 내용은 무엇인가요?',
      wikiSummary: '이 Wiki 페이지의 핵심 내용은 무엇인가요?',
      documentSummary: '이 문서의 핵심 결론은 무엇인가요?',
      recentActivity: '최근에 업로드되거나 수정된 문서는 무엇인가요?',
      agents: '이 에이전트들은 각각 어떤 질문에 적합한가요?',
      messageSources: '이 답변의 근거는 무엇인가요?',
      messageCheck: '이 답변에 틀린 내용이 있나요?',
      modelCheck: '이 모델의 설정은 현재 용도에 적합한가요?',
      modelUsage: '어떤 에이전트와 지식베이스가 이 모델들을 쓰나요?',
      mcpTools: '이 MCP 서비스는 어떤 도구를 제공하나요?',
      mcpCheck: '이 서비스를 사용하려면 무엇을 더 설정해야 하나요?',
      modelSetup: '어떤 모델을 더 설정해야 하나요?',
      mcpSetup: 'MCP 서비스는 어떻게 연결하나요?',
      releaseHighlights: '현재 버전에서 주로 무엇이 바뀌었나요?',
      gettingStarted: 'Xiaozhi를 처음 사용할 때 무엇부터 설정해야 하나요?',
      workflow: '지식 베이스, 에이전트, 자동화를 어떻게 함께 활용하나요?',
      knowledgeOverview: '각 지식 베이스에서 어떤 내용을 찾을 수 있나요?',
      knowledgeType: '문서, FAQ, Wiki는 어떻게 구분해서 사용하나요?',
      knowledgeOrganize: '가지고 있는 자료를 유용한 지식 베이스로 정리하려면 어떻게 해야 하나요?',
      knowledgeTopics: '이 문서들은 각각 무엇을 다루나요?',
      knowledgeGaps: '파싱에 실패했거나 아직 끝나지 않은 문서는 무엇인가요?',
      faqCoverage: '이 FAQ는 어떤 자주 묻는 질문을 다루나요?',
      faqDuplicates: '내용이 겹쳐서 합칠 수 있는 FAQ는 무엇인가요?',
      faqImprove: '보완하거나 업데이트해야 할 답변은 무엇인가요?',
      documentSteps: '이 문서의 방법을 따라 할 수 있는 절차로 정리해 줘',
      documentFaq: '이 문서에서 어떤 FAQ를 만들 수 있나요?',
      wikiSources: '이 Wiki 페이지의 결론을 뒷받침하는 출처는 무엇인가요?',
      agentCreate: '지식 베이스를 검색하는 에이전트는 어떻게 만드나요?',
      agentChoose: '지식 베이스를 찾을 때는 여기 에이전트 중 어떤 것을 쓰면 되나요?',
      automationIdeas: '어떤 반복 작업을 자동화하면 좋을까요?',
      automationCreate: '지식 베이스 업데이트를 매주 요약하는 작업을 설정해 줘',
      automationOverview: '최근 제 자동화 작업은 잘 실행되고 있나요?',
      automationSummary: '이 작업의 최근 실행에서 어떤 결과가 나왔나요?',
      automationSchedule: '이 작업은 다음에 언제 실행되나요?',
      automationImprove: '이 작업의 프롬프트와 실행 일정을 어떻게 개선할 수 있나요?',
      skillFind: '여기 스킬 중 에이전트에 넣으면 좋은 것은 무엇인가요?',
      skillAdd: '새 스킬을 추가하고 에이전트에서 활성화하려면 어떻게 하나요?',
      skillUse: '추가된 각 스킬로 무엇을 할 수 있나요?',
      mcpFind: '이 MCP 서비스에서 에이전트가 호출할 수 있는 도구는 무엇인가요?',
      mcpExamples: '에이전트가 이 MCP 도구를 사용하게 하려면 어떻게 하나요?',
      mcpUsage: '이 서비스 도구를 어떻게 쓰는지 예를 보여 줘',
      modelFit: '이 모델은 어떤 작업에 더 적합한가요?',
      modelTypes: '대화, 임베딩, 리랭킹 모델은 각각 어떻게 선택하나요?',
      browserConnect: '에이전트가 사용할 브라우저를 어떻게 연결하나요?',
      browserTasks: '브라우저로 어떤 웹 작업을 자동화할 수 있나요?',
      browserReconnect: '브라우저가 오프라인으로 표시되면 어떻게 다시 연결하나요?',
      messageReuse: '이 답변을 따라 할 수 있는 단계로 정리해 줘',
      chatSummary: '이번 대화에서는 무엇을 물었고, 어떤 결과를 얻었나요?',
      chatCheck: '마지막 답변에 빠지거나 잘못된 내용이 있나요?',
      chatFollowup: '이번 대화를 바탕으로 이어서 무엇을 물어볼 수 있나요?',
      artifactRecent: '최근에 생성된 파일은 무엇인가요?',
      artifactSources: '이 파일들은 각각 어느 대화에서 왔나요?',
      artifactCreate: '에이전트가 결과를 파일로 저장하게 하려면 어떻게 하나요?',
      organizationShared: '이 공유 공간들에는 각각 어떤 지식 베이스와 에이전트가 있나요?',
      organizationJoin: '이미 있는 공유 공간에 어떻게 참여하나요?',
      organizationCreate: '공유 공간을 만들고 멤버를 초대하려면 어떻게 하나요?'
    },
    context: {
      currentPage: '현재 페이지',
      detach: '현재 페이지 포함하지 않기',
      attachedTip: '현재 페이지 포함됨: {path}',
      detachedTip: '클릭하여 현재 페이지 포함: {path}',
      chatMessage: '이 답변',
      pages: {
        knowledge_base: '지식베이스',
        wiki: 'Wiki',
        agent_editor: '에이전트 편집',
        settings_models: '모델 관리',
        mcp_services: 'MCP 서비스',
        settings: '설정',
        chat: '대화'
      }
    },
    access: {
      title: '권한 수준',
      capped: '워크스페이스 관리자가 허용하지 않았습니다',
      levels: {
        auto_write: {
          label: '자동 실행',
          desc: '되돌릴 수 있는 변경은 바로 실행하고, 삭제는 여전히 확인합니다'
        },
        confirm: {
          label: '변경 전 확인',
          desc: '변경하거나 삭제할 때마다 먼저 확인을 요청합니다'
        },
        read_only: {
          label: '읽기 전용',
          desc: '확인만 하고 아무것도 변경하지 않습니다'
        }
      },
      page: {
        label: '현재 페이지 보기 및 입력',
        desc: '왼쪽 페이지를 읽고 양식을 대신 입력할 수 있습니다. 버튼을 누르거나 저장하지 않습니다.'
      }
    },
    fillNotice: {
      title: '어시스턴트가 {count}곳을 입력했습니다',
      undo: '되돌리기',
      dismiss: '닫기'
    },
    bubble: {
      label: '어시스턴트 빠른 작업',
      ask: '어시스턴트에게 묻기',
      polish: '다듬기',
      rewrite: '다시 쓰기',
      translate: '번역',
      continue: '이어 쓰기',
      prompts: {
        polish: '선택한 내용을 다듬어 주세요. 오타와 어색한 표현을 고치되 의미는 바꾸지 말고 그 자리에서 바꿔 주세요.',
        rewrite: '선택한 내용을 더 명확하고 간결하게 다시 써서 그 자리에서 바꿔 주세요.',
        translate: '선택한 내용을 번역해 주세요. 중국어는 영어로, 다른 언어는 중국어로 옮겨 그 자리에서 바꿔 주세요.',
        continue: '선택한 내용 뒤에 문맥에 맞는 문단을 하나 이어 써 주세요.'
      }
    },
    selection: {
      label: '선택됨',
      lines: '{count}줄 선택됨',
      detach: '선택한 내용 빼기',
      tip: '보낼 때 선택한 내용을 함께 보냅니다: {text}',
      tipField: '보낼 때 「{field}」에서 선택한 내용을 함께 보냅니다: {text}'
    },
    prompts: {
      createAgent: '이 요청에 맞는 에이전트를 만드세요: {request}. 사용 가능한 모델, 지식 베이스, MCP, 스킬을 확인해 선택하세요. 꼭 필요한 누락 정보만 질문하고 현재 권한 정책을 따르며 생성 후 편집 화면을 열어 주세요.',
      createAutomation: '예약 작업을 만드세요: {request}. 별도 지정이 없으면 시간대 {timezone}을 사용하세요. 독립적으로 실행 가능한 지침을 작성하고 일정을 검증해 다음 실행 시간을 보여 주세요. 실행 권한을 높이지 말고 현재 정책을 따르며 생성 후 작업을 열어 주세요.',
      summarizeActivity: '이 필터 스냅샷의 loaded_entry_ids만 요약하세요: {scope}. 같은 조건으로 조회하고 필요하면 페이지를 추가 조회하세요. 대상 자료, 작업자, 결과를 설명하고 감사 기록과 본문 변경을 구분하세요. 로드된 기록을 전체로 간주하지 마세요.',
      explainMcpTools: 'MCP 서비스 {id}의 저장된 도구 목록을 읽고 기능과 유용한 질문 예시 세 가지를 설명하세요. 오래되거나 불완전한 정보는 표시하고 새로고침, 도구 실행, 설정 변경은 하지 마세요.',
      answerToDocument: '이 답변과 원래 질문을 읽고 출처와 불확실성을 유지한 문서 초안을 작성하세요: {source}. 초안을 보여 주고 대상 지식 베이스를 확인한 뒤 현재 권한으로 생성하세요. 기존 자료는 덮어쓰지 마세요.',
      answerToFaq: '이 답변과 원래 질문으로 표준 질문과 정확한 답변을 작성하세요: {source}. 초안을 보여 주고 대상 FAQ 지식 베이스를 확인하며 유사 항목을 검사한 뒤 현재 권한으로 저장하세요. 기존 항목은 덮어쓰지 마세요.',
      answerToAutomation: '답변과 질문 {source}의 반복 작업을 독립 실행 가능한 예약 작업으로 정리하세요. 누락된 주기, 시간, 시간대를 질문하고 다음 실행을 검증해 보여 준 뒤 현재 권한으로 생성하세요. 실행 권한을 높이지 마세요.',
      writePrompt: '현재 에이전트의 목적과 설정에 맞는 시스템 프롬프트를 작성해 주세요. 목표가 불분명하면 먼저 질문해 주세요. 템플릿 자리 표시자를 유지하고 제안을 현재 편집기에 입력해 주세요. 저장된 에이전트를 변경하거나 저장하지 마세요.',
      refinePrompt: '첨부한 시스템 프롬프트의 역할, 응답 요구사항, 도구 사용 규칙을 더 명확하게 개선해 주세요. 원래 의도와 템플릿 자리 표시자를 유지하고 수정 내용을 현재 편집기에 입력해 주세요. 저장된 에이전트를 변경하거나 저장하지 마세요.',
      modelFailure: '현재 모델 설정과 첨부한 연결 오류를 바탕으로 실패 원인을 분석하고 점검 단계를 제안해 주세요. 인증 정보를 읽거나 표시하지 말고 설정을 변경하거나 저장하지 마세요.',
      mcpFailure: 'MCP 서비스(ID: {id})를 확인하고 첨부된 도구 조회 또는 동기화 오류의 원인과 점검 절차를 설명해 주세요. 자격 증명을 읽거나 표시하지 말고 재연결이나 설정 변경도 하지 마세요.',
      syncFailure: '데이터 소스 "{source}"(ID: {id})의 동기화 로그(ID: {log})를 확인하고 첨부된 오류 사례와 실패 건수로 원인과 해결 방법을 설명해 주세요. 동기화를 재시도하거나 데이터 소스를 수정하지 마세요.',
      writeWikiRules: '현재 지식베이스의 용도에 맞게 "{field}"의 명확한 규칙을 작성해 주세요. 용도가 불분명하면 먼저 질문해 주세요. 해당 입력란에 작성하고 시스템의 인용 및 출력 규약을 유지해 주세요. 저장하거나 다시 파싱하지 마세요.',
      refineWikiRules: '첨부된 "{field}" 규칙의 의미를 유지하면서 더 명확하게 개선해 주세요. 해당 입력란에 작성하고 시스템의 인용 및 출력 규약을 유지해 주세요. 저장하거나 다시 파싱하지 마세요.',
      analyzeChunks: '첨부된 분할 미리보기의 원문과 청크 발췌, 실행 당시 매개변수, 통계를 바탕으로 의미 단절이나 지나치게 짧거나 긴 청크를 분석하고 조정안을 제안해 주세요. 발췌로 확인 가능한 문제와 추가 원문이 필요한 판단을 구분해 주세요. 설정 변경이나 지식베이스 재구축은 하지 마세요.'
    },
    actions: {
      summarizeActivity: '현재 {count}개 변경 내역 요약',
      toolExamples: '사용 예시 보기',
      answerToDocument: '문서로 정리',
      answerToFaq: 'FAQ로 저장',
      answerToAutomation: '예약 작업으로 만들기',
      writePrompt: '작성 도움',
      refinePrompt: '프롬프트 개선',
      diagnose: '원인 분석',
      refineRules: '규칙 개선',
      analyzeChunks: '청크 결과 분석'
    },
    create: {
      agentTitle: '자연어로 에이전트 만들기',
      agentAction: '어시스턴트로 만들기',
      agentHint: '누구를 위해 어떤 일을 해야 하는지 설명하면 어시스턴트가 리소스를 선택하고 생성합니다.',
      agentPlaceholder: '예: 제품 지식 베이스로 질문에 답하고 출처를 제시하며 정보가 없으면 알려주는 고객 지원 에이전트.',
      automationTitle: '어시스턴트로 작업 만들기',
      automationHint: '할 일과 실행 시간을 설명하면 어시스턴트가 자동화 작업으로 정리합니다.',
      automationPlaceholder: '예: 매주 금요일 오후 5시에 제품 지식 베이스의 이번 주 업데이트를 요약해 주세요.',
      requestLabel: '작업 설명',
      manual: '직접 설정',
      start: '어시스턴트에게 맡기기'
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
      knowledgeBases: '지식 베이스 유형을 선택하고 자료를 정리하며, 질문에 맞는 정보 출처를 찾도록 도와드립니다.',
      knowledgeBase: '이 문서들이 무엇을 다루는지, 최근 업데이트, 아직 파싱이 끝나지 않은 파일을 정리할 수 있습니다.',
      document: '문서의 핵심과 작업 절차를 정리하거나, 내용을 바탕으로 FAQ를 작성할 수 있습니다.',
      faq: 'FAQ가 다루는 범위와 중복 질문을 확인하고, 답변을 더 명확하게 다듬도록 도와드립니다.',
      wiki: '페이지 내용과 인용 출처를 확인하고, 보완하거나 갱신할 부분을 찾도록 도와드립니다.',
      agents: '무엇을 하고 싶은지 알려주세요. 적합한 모델, 지식 베이스, 도구를 갖춘 에이전트 생성을 도와드립니다.',
      automation: '반복 작업을 예약하고, 실행 결과를 검토하며, 실행 일정을 조정하도록 도와드립니다.',
      skills: '작업 목표를 알려주세요. 스킬을 찾고 추가한 뒤 적합한 에이전트에서 사용하도록 설정을 도와드립니다.',
      mcp: 'MCP 서비스를 찾아 연결하고, 사용 가능한 도구를 살펴보고, 에이전트에서 사용하도록 설정을 도와드립니다.',
      browser: '브라우저 연결 방법, 자동화에 적합한 작업, 필요한 권한을 안내해 드립니다.',
      model: '모델을 연결하고 용도를 비교하며, 작업에 맞는 설정인지 확인하도록 도와드립니다.',
      chat: '이번 대화에서 무엇을 물었고 무엇을 얻었는지 요약하고, 마지막 답변을 확인한 뒤 다음에 무엇을 물을지 제안할 수 있습니다.',
      message: '이 답변의 출처와 주요 정보를 확인하고, 재사용하기 좋은 내용으로 정리하도록 도와드립니다.',
      artifacts: '이 파일들을 시간과 유형별로 정리하고, 어느 대화에서 왔는지 찾으며, 에이전트가 결과를 파일로 저장하게 하는 방법을 설명할 수 있습니다.',
      organizations: '각 공유 공간에 어떤 지식 베이스와 에이전트가 있는지, 그리고 만들고 참여하거나 멤버를 초대하는 방법을 안내할 수 있습니다.'
    },
    help: {
      label: '어시스턴트 설명',
      title: 'Xiaozhi 어시스턴트가 할 수 있는 일',
      identity: '어시스턴트는 사용자 본인으로 동작합니다. 보고 수정할 수 있는 범위는 이 공간에서 가진 역할과 같으며, 그 권한을 넘지 않습니다.',
      page: '열면 현재 페이지가 함께 붙습니다. 화면의 내용을 정리하고, 에이전트와 자동화를 설정하거나, 양식을 대신 채울 수 있습니다. 버튼을 누르거나 저장하지는 않습니다.',
      access: '입력창 아래에서 권한을 바꿀 수 있습니다. 읽기 전용, 수정 전 확인, 되돌릴 수 있는 수정은 자동 실행. 삭제는 항상 확인이 필요하며, 관리자가 정한 상한은 넘을 수 없습니다.'
    },
    layout: {
      dock: '오른쪽에 고정',
      float: '떠 있는 창으로 전환'
    }
  },
  preview: {
    loading: '문서 미리보기 로딩 중...',
    loadFailed: '문서 미리보기 로드 실패',
    retry: '재시도',
    unsupported: '이 파일 유형은 온라인 미리보기를 지원하지 않습니다',
    unsupportedHint: '파일을 다운로드하여 로컬 앱으로 열어주세요',
    zoomIn: '확대',
    zoomOut: '축소',
    fullscreen: '전체 화면',
    exitFullscreen: '전체 화면 종료',
    htmlRendered: '렌더링 미리보기',
    htmlSource: '원본 보기',
    audioNotSupported: '브라우저가 오디오 재생을 지원하지 않습니다',
    videoNotSupported: '브라우저가 동영상 재생을 지원하지 않습니다'
  },
  organization: {
    owner: '소유자',
    roleUpdated: '역할이 업데이트되었습니다.',
    roleUpdateFailed: '역할을 업데이트하지 못했습니다.',
    createdByMe: '내가 생성한',
    joinedByMe: '내가 참여한',
    share: {
      title: '공유 공간에 공유',
      selectOrg: '공유 공간 선택',
      selectOrgPlaceholder: '공유할 공유 공간을 선택해주세요',
      permission: '권한',
      permissionTip: '편집 가능한 권한을 통해 구성원은 지식베이스 콘텐츠를 수정할 수 있으며, 읽기 전용 권한은 검색 및 Q&A만 허용합니다.',
      shareSuccess: '공유 완료',
      shareFailed: '공유 실패',
      unshareSuccess: '공유되지 않음',
      unshareFailed: '공유를 취소하지 못했습니다.',
      sharedTo: '공유된 스페이스',
      noShares: '아직 어떤 공유 공간에도 공유되지 않았습니다.',
      searchPlaceholder: '공유 공간 검색…',
      loading: '로딩 중…',
      emptySearch: '「{q}」와(과) 일치하는 공유 공간이 없습니다',
      addShareDialogTitle: '공유 공간에 공유',
      unshareAction: '공유 해제',
      sharedFrom: '출처',
      permissionReadonly: '읽기 전용',
      permissionEditable: '편집 가능',
      columns: {
        space: '공유 공간',
        permission: '권한',
        sharedAt: '공유 시간',
        operations: '작업'
      }
    },
    settings: {
      pendingJoinRequestsBadge: '가입 신청 대기 중'
    },
    role: {
      admin: '관리자',
      editor: '편집자',
      viewer: '읽기 전용'
    },
    join: {
      title: '공유 공간에 참여하기'
    }
  },
  promptTemplate: {
    noTemplates: '아직 템플릿이 없습니다.',
    selectTemplate: '템플릿 선택',
    useTemplate: '템플릿 사용',
    resetDefault: '기본값 복원',
    default: '기본',
    withKnowledgeBase: '지식베이스',
    withWebSearch: '웹 검색'
  },
  mcpServiceDialog: {
    addTitle: 'MCP 서비스 추가',
    addDesc: '외부 MCP 서비스를 연결하면 에이전트가 해당 도구를 호출할 수 있습니다.',
    editTitle: 'MCP 서비스 편집',
    basicSection: '기본',
    connectionSection: '연결',
    enableServiceDesc: '비활성화 시 이 서비스가 호출되지 않습니다',
    unitSecond: '초',
    name: '서비스 이름',
    namePlaceholder: '서비스 이름을 입력해주세요',
    transportType: '전송 유형',
    serviceUrl: '서비스 URL',
    serviceUrlPlaceholder: 'https://example.com/mcp',
    enableService: '서비스 활성화',
    authConfig: '인증 설정',
    authType: '인증 방식',
    authTypeNone: '없음 / 사용자 정의 헤더',
    authTypeApiKey: 'API Key / Token',
    authTypeOAuth: 'OAuth 2.0(최초 연결 시 인증)',
    oauthScopes: '스코프(선택, 공백으로 구분)',
    oauthClientId: '클라이언트 ID(선택)',
    oauthClientIdDesc: '인가 서버에 미리 등록한 클라이언트입니다. 비워 두면 동적 클라이언트 등록으로 자동 등록합니다. 클라이언트 ID를 바꾸면 시크릿도 함께 바꿔 주세요.',
    oauthClientSecret: '클라이언트 시크릿(선택)',
    oauthAuthorization: '인증 상태',
    oauthAuthorized: '인증됨',
    oauthRefreshable: '토큰이 만료되었습니다. 다음 사용 시 자동으로 갱신됩니다',
    oauthUnauthorized: '미인증',
    oauthAuthorize: '인증하기',
    oauthReauthorize: '재인증',
    oauthRevoke: '인증 해제',
    oauthAuthorizeHint: '「인증하기」를 클릭하면 현재 설정을 먼저 자동 저장한 후 인증을 시작합니다(사용자별 개별 인증).',
    apiKeyHeader: '요청 헤더 이름',
    apiKeyHeaderDesc: '비워 두면 기본값은 X-API-Key입니다. Bearer 방식은 Authorization을 입력하고 아래 비밀 값에 "Bearer <token>"을 작성하세요. 원시 토큰이 필요하면 Authorization에 토큰을 그대로 입력합니다.',
    credentialValue: '비밀 값 / 토큰',
    optional: '선택',
    advancedConfig: '고급 설정',
    timeoutSec: '타임아웃(초)',
    codeImport: {
      toggle: '코드에서 가져오기',
      hint: '표준 mcpServers JSON 설정을 붙여넣으면 양식이 자동으로 채워집니다',
      parse: '파싱 후 채우기',
      editOverwriteHint: '가져오기는 현재 양식을 덮어씁니다(저장된 자격 증명은 영향받지 않으며, 저장을 눌러야 적용됩니다)',
      toasts: {
        filled: '양식이 채워졌습니다. 확인 후 저장해 주세요',
        multipleServers: '여러 서비스가 감지되어 첫 번째 항목을 가져왔습니다: {name}'
      },
      errors: {
        empty: '먼저 설정을 붙여넣어 주세요',
        invalidJson: '파싱할 수 없습니다. JSON 형식을 확인해 주세요',
        noServer: 'MCP 서비스 설정을 찾을 수 없습니다',
        missingUrl: '설정에 url이 없습니다',
        stdioUnsupported: 'stdio(command/args) 설정은 지원되지 않습니다. url이 포함된 원격 설정을 사용해 주세요'
      }
    },
    customHeaders: {
      label: '사용자 지정 헤더(선택 사항)',
      desc: '모든 MCP 요청에 추가되는 HTTP 헤더로, 기업 게이트웨이 인증, 추적 등에 자주 사용됩니다.',
      add: '헤더 추가',
      keyPlaceholder: '헤더 이름',
      valuePlaceholder: '헤더 값'
    },
    toasts: {
      updated: 'MCP 서비스가 업데이트되었습니다',
      updateFailed: 'MCP 서비스 업데이트 실패',
      authorized: '인증이 완료되었습니다',
      authorizeFailed: '인증을 시작하지 못했습니다',
      revoked: '인증이 해제되었습니다',
      revokeFailed: '인증 해제에 실패했습니다'
    },
    rules: {
      nameRequired: '서비스 이름을 입력해주세요',
      transportRequired: '전송 유형을 선택해주세요',
      urlRequired: '서비스 URL을 입력해주세요',
      urlInvalid: '유효한 URL을 입력해주세요'
    }
  },
  mcpMetadata: {
    searchTools: '도구 이름 또는 설명 검색',
    retry: '다시 시도',
    details: '상세',
    description: '설명',
    parameters: '매개변수',
    required: '필수',
    fullSchema: '전체 정의',
    noDescription: '설명이 없습니다',
    noParameters: '매개변수 정의가 없습니다',
    enabled: '활성화',
    approval: '승인 필요',
    noTools: '일치하는 도구가 없습니다',
    next: '다음',
    policyLoadFailed: '도구 정책을 불러오지 못했습니다. 수정하기 전에 다시 시도하세요.',
    policySaveFailed: '도구 설정을 저장하지 못했습니다',
    tools: 'Tools 목록',
    cacheHint: '아직 동기화되지 않았다면 이 단계에서 자동으로 연결해 저장합니다. 이후에는 새로 고침할 때만 MCP 서버에 연결합니다.',
    fetch: '다시 가져오기',
    fetching: '연결해서 Tools를 가져오는 중…',
    toolCount: '도구 {count}개',
    stale: '연결 또는 인증 설정이 변경되었습니다. 모델이 사용하기 전에 목록을 새로 고치세요.',
    notSynced: '아직 동기화되지 않았습니다. 가져오면 전체 설명과 매개변수 정의가 저장됩니다.',
    syncRequired: '먼저 연결해서 Tools를 가져온 뒤 저장하세요. 모델은 동기화된 목록만 사용할 수 있습니다.',
    syncedAt: '동기화 시간:',
    serverDocumentation: '서버 원본 설명',
    noServerDocumentation: '이 MCP 서버의 initialize 응답에 instructions / serverInfo.description이 없습니다(둘 다 선택 필드). 도구 설명은 아래 각 도구의 description에 있습니다.',
    policyHint: '도구 활성화 및 승인 설정은 즉시 저장되며 목록을 새로 고쳐도 유지됩니다.',
    columnTool: '도구',
    columnEnabled: '활성화',
    columnApproval: '승인',
    failed: '도구 목록을 불러오지 못했습니다',
    setupProgress: 'MCP 설정 단계',
    connection: '연결 설정',
    toolsAndUsage: '도구 및 용도',
    previous: '이전',
    usage: '서비스 용도',
    usageHint: '모델은 이 개요를 읽은 후 필요한 도구를 불러옵니다. 새로 고침해도 입력한 내용은 유지됩니다.',
    usageInstructions: '사용 안내',
    instructionsPlaceholder: '서비스의 용도, 사용 상황, 주요 제약을 간결하게 설명하세요.',
    generateUsage: 'AI로 생성',
    generateHint: '동기화된 활성 도구를 바탕으로 간결한 안내를 생성합니다. 수정 후 저장하면 적용됩니다.',
    instructionsRequired: '사용 안내를 입력해 주세요',
    generated: '생성되었습니다. 검토 후 저장해 주세요.',
    generateFailed: '생성에 실패했습니다. 도구 동기화와 사용 가능한 대화 모델 설정을 확인한 후 다시 시도하세요.'
  },
  ollamaSettings: {
    installed: {
      title: '다운로드된 모델',
      desc: 'Ollama에 설치된 모델 목록'
    },
    download: {
      title: '새 모델 다운로드'
    },
    address: {
      desc: '로컬 Ollama 서비스의 API 주소, 시스템에서 자동으로 감지됩니다. 수정이 필요하면 .env 설정 파일에서 설정해주세요'
    },
    status: {
      desc: '로컬 Ollama 서비스의 사용 가능 여부를 자동으로 감지합니다. 서비스가 실행되지 않거나 주소 설정이 잘못되면 "사용 불가" 상태가 표시됩니다'
    }
  },
  modelSettings: {
    moreActions: '추가 작업',
    title: '모델 설정',
    copySuffix: ' 사본',
    builtinTag: '기본제공',
    confirmDelete: '모델 "{name}"을(를) 삭제하시겠습니까?',
    debug: {
      reasoningEffort: '사고 강도',
      reasoningEffortDesc: '모델 카탈로그가 보고한 수준으로 reasoning_effort를 보냅니다',
      title: '모델 테스트',
      description: '저장된 모델 설정으로 요청을 보냅니다. 편집 중인 변경 사항은 저장 후 반영됩니다.',
      groupModel: '모델 선택',
      groupInput: '테스트 입력',
      groupResult: '실행 결과',
      modelType: '모델 유형',
      model: '모델',
      modelPlaceholder: '테스트할 모델을 선택하세요',
      noModelsForType: '이 유형의 저장된 모델이 없습니다',
      query: '입력 내용',
      queryPlaceholder: '모델에 보낼 내용을 입력하세요',
      embeddingInput: '벡터화할 텍스트',
      embeddingPlaceholder: 'Embedding을 생성할 텍스트를 입력하세요',
      vlmPrompt: '이미지 프롬프트',
      vlmPromptPlaceholder: '예: 이 이미지를 자세히 설명해 주세요',
      documents: '후보 문서',
      documentsPlaceholder: '후보 문서를 한 줄에 하나씩 입력하세요',
      documentsHint: '비어 있지 않은 각 줄은 ReRank 모델에 별도 문서로 전송됩니다',
      imageFile: '이미지 파일',
      similarityMode: '유사도',
      similarityQuery: '쿼리',
      similarityQueryPlaceholder: '쿼리를 입력하세요. 예: 잔디 위를 달리는 개',
      similarityCandidates: '후보 텍스트',
      similarityCandidatesPlaceholder: '한 줄에 하나의 후보 텍스트를 입력하세요',
      similarityHint: '쿼리는 검색 쿼리로, 후보는 문서로 벡터화됩니다(실제 검색과 동일). 결과는 코사인 유사도가 높은 순으로 정렬됩니다',
      similarityImage: '후보 이미지(선택)',
      similarityImageCandidate: '이미지',
      audioFile: '오디오 파일',
      chooseFile: '파일 선택',
      parameters: '요청 매개변수',
      systemPrompt: 'System Prompt',
      systemPromptPlaceholder: '선택 사항, 시스템 프롬프트 입력',
      run: '테스트 실행',
      copyResult: '결과 복사',
      history: '기록',
      runLabel: '{n}번째 실행',
      success: '호출 성공',
      failed: '호출 실패',
      rawResponse: '응답 내용',
      requestPreview: '요청 미리보기',
      requestFailed: '모델 테스트 요청 실패',
      metrics: {
        api: '프로토콜',
        thinkingFormat: '사고 형식',
        requestedReasoningEffort: '요청한 강도',
        dimension: '벡터 차원',
        resultCount: '결과 수',
        answerChars: '답변 문자 수',
        reasoningChars: '추론 문자 수',
        reasoningReturned: '추론 내용 반환',
        textChars: '전사 문자 수',
        segmentCount: '세그먼트 수'
      }
    },
    usage: {
      title: '모델을 삭제할 수 없습니다',
      description: '모델 "{name}"이(가) 다음 설정에서 사용 중입니다. 각 설정을 열어 다른 모델로 변경한 후 다시 삭제하세요.',
      knowledgeBases: '지식 베이스 ({count})',
      agents: '에이전트 ({count})',
      openConfiguration: '설정 열기',
      truncated: '전체 {total}개 중 앞 {shown}개만 표시합니다',
      longTermMemory: '장기 메모리'
    },
    builtinModels: {
      title: '기본 제공 모델',
      description: '기본 제공 모델은 모든 워크스페이스에게 표시됩니다. 민감한 정보는 숨겨지며, 편집하거나 삭제할 수 없습니다.',
      descriptionAdmin: '기본 제공 모델은 모든 워크스페이스에게 표시됩니다. 시스템 관리자는 구성과 자격 증명을 편집할 수 있으며, 삭제는 배포 구성에서 관리됩니다.',
      viewGuide: '기본 제공 모델 관리 가이드 보기'
    },
    toasts: {
      nameRequired: '모델 이름은 비워둘 수 없습니다',
      nameTooLong: '모델 이름은 100자를 초과할 수 없습니다',
      displayNameTooLong: '표시 이름은 100자를 초과할 수 없습니다',
      baseUrlRequired: 'Remote API 유형은 Base URL이 필수입니다',
      baseUrlInvalid: 'Base URL 형식이 올바르지 않습니다. 유효한 URL을 입력해주세요',
      dimensionInvalid: 'Embedding 모델은 유효한 벡터 차원(128-4096)을 입력해야 합니다',
      updated: '모델이 업데이트되었습니다',
      added: '모델이 추가되었습니다',
      saveFailed: '모델 저장 실패',
      deleted: '모델이 삭제되었습니다',
      deleteFailed: '모델 삭제 실패',
      builtinCannotEdit: '기본 제공 모델은 편집할 수 없습니다',
      linkedModelMissing: '어시스턴트가 연결한 모델을 찾을 수 없습니다. 삭제되었을 수 있습니다',
      builtinCannotDelete: '기본 제공 모델은 삭제할 수 없습니다',
      builtinCannotCopy: '기본 제공 모델은 복사할 수 없습니다',
      copied: '모델이 복사되었습니다',
      copyFailed: '모델 복사에 실패했습니다'
    },
    asr: {
      title: 'ASR 음성 모델',
      desc: '음성 인식 및 오디오 전사를 위한 음성 인식 모델 설정 (예: OpenAI Whisper)',
      empty: 'ASR 음성 모델 없음'
    },
    vllm: {
      title: 'VLLM 비전 모델',
      desc: '시각 이해 및 멀티모달용 비전 언어 모델 설정',
      empty: 'VLLM 비전 모델 없음'
    },
    rerank: {
      title: 'ReRank 모델',
      desc: '결과 재정렬용 모델 설정',
      empty: 'ReRank 모델 없음'
    },
    embedding: {
      title: 'Embedding 모델',
      desc: '텍스트 벡터화용 임베딩 모델 설정',
      empty: 'Embedding 모델 없음'
    },
    chat: {
      title: '대화 모델',
      desc: '대화용 대규모 언어 모델 설정',
      empty: '대화 모델 없음'
    },
    source: {
      remote: 'Remote',
      openaiCompatible: 'OpenAI 호환',
      custom: '사용자 지정'
    },
    actions: {
      addModel: '모델 추가',
      debugModel: '모델 테스트'
    },
    typeShort: {
      chat: '대화',
      embedding: 'Embedding',
      rerank: 'ReRank',
      vllm: '비전',
      asr: '음성'
    }
  },
  mcpSettings: {
    addUsageInstructions: '사용 안내 추가',
    noUsageInstructions: '아직 사용 안내가 없습니다',
    title: 'MCP 서비스 관리',
    description: '외부 MCP (Model Context Protocol) 서비스를 관리합니다. Agent 모드에서 외부 도구와 리소스를 호출합니다',
    enabled: '활성화됨',
    disabled: '비활성화됨',
    addService: '서비스 추가',
    empty: 'MCP 서비스 없음',
    deleteConfirmBody: 'MCP 서비스 "{name}"을(를) 삭제하시겠습니까? 이 작업은 취소할 수 없습니다.',
    unnamed: '이름 없음',
    builtin: '내장',
    toolCount: '{count}개 도구',
    toolsNotSynced: '도구가 아직 동기화되지 않음',
    toolsStale: '다시 동기화 필요',
    toasts: {
      loadFailed: 'MCP 서비스 목록 로드 실패',
      enabled: 'MCP 서비스가 활성화되었습니다',
      disabled: 'MCP 서비스가 비활성화되었습니다',
      updateStateFailed: 'MCP 서비스 상태 업데이트 실패',
      linkedServiceMissing: '어시스턴트가 연결한 MCP 서비스를 찾을 수 없습니다. 삭제되었을 수 있습니다',
      deleted: 'MCP 서비스가 삭제되었습니다',
      deleteFailed: 'MCP 서비스 삭제 실패'
    }
  },
  conversationSettings: {
    maxTokens: {
      desc: '생성 답변의 최대 토큰 수'
    },
    temperature: {
      desc: '모델 출력의 무작위성을 제어합니다. 0은 가장 확정적, 1은 가장 무작위'
    },
    systemPrompt: {
      desc: '일반 모드 대화를 위한 시스템 수준 Prompt'
    },
    contextTemplate: {
      desc: '일반 모드에서 검색 결과를 기반으로 답변을 생성하는 Prompt 템플릿'
    },
    rerankModel: {
      desc: '검색 결과 재정렬을 위한 모델 (선택)'
    },
    chatModel: {
      desc: '요약 및 개요를 위한 대규모 언어 모델'
    },
    rewritePrompt: {
      desc: '질문 재작성을 제어하는 시스템 프롬프트'
    },
    fallbackPrompt: {
      desc: '모델 폴백을 선택했을 때 사용되는 프롬프트 템플릿'
    },
    fallbackResponse: {
      desc: '폴백 전략이 고정 응답일 때 반환되는 텍스트'
    },
    fallbackStrategy: {
      desc: '검색 결과가 없을 때 처리 방식'
    },
    enableQueryExpansion: {
      desc: '검색 결과가 부족할 때 대규모 모델을 호출해 확장 쿼리를 생성합니다 (지연 시간 및 비용 증가)'
    },
    enableRewrite: {
      desc: '다중 턴 대화에서 더 나은 검색을 위해 질문을 자동으로 재작성합니다'
    },
    rerankThreshold: {
      desc: '재정렬 단계의 최소 점수 임계값'
    },
    rerankTopK: {
      desc: '재정렬 후 답변 생성에 사용될 문서 수'
    },
    vectorThreshold: {
      desc: '벡터 검색의 최소 유사도 임계값'
    },
    keywordThreshold: {
      desc: '키워드 검색의 최소 점수 임계값'
    },
    embeddingTopK: {
      desc: '벡터 검색 단계에서 유지할 문서 수'
    },
    maxRounds: {
      desc: '다중 턴 컨텍스트 및 질문 재작성에 사용되는 히스토리 턴 수'
    },
    models: {
      chatGroupLabel: '사고 / 대화 모델'
    }
  },
  agentSettings: {
    systemPrompt: {
      desc: 'Agent의 시스템 프롬프트를 설정합니다. 플레이스홀더 템플릿을 지원합니다. 플레이스홀더는 런타임에 자동으로 실제 내용으로 대체됩니다.'
    },
    allowedTools: {
      desc: '현재 Agent가 사용할 수 있는 도구 목록'
    },
    temperature: {
      desc: '모델 출력의 무작위성을 제어합니다. 0은 가장 확정적, 1은 가장 무작위'
    },
    rerankModel: {
      desc: '검색 결과 재정렬, 다양한 소스의 관련성 점수 통합'
    },
    thinkingModel: {
      desc: 'Agent 추론 및 계획을 위한 LLM 모델'
    },
    maxIterations: {
      desc: 'Agent가 한 작업에서 수행할 최대 추론 단계 수입니다. 「제한 없음」을 선택하면 모델이 스스로 끝나거나 직접 중지할 때까지 계속 실행됩니다.'
    },
    modelRecommendation: {
      title: '모델 추천'
    }
  },
  uploadTasks: {
    panelLabel: '업로드',
    titleUploading: '업로드 중 {done}/{total}',
    titleParsing: '파싱 중 {done}/{total}',
    titleDone: '모두 완료',
    titleDoneWithIssues: '{ok}개 완료, {bad}개 미완료',
    titleCancelled: '업로드가 취소되었습니다',
    destination: '업로드 위치: {name}',
    destinationMany: '업로드 위치: 지식베이스 {count}개',
    remaining: '약 {time} 남음',
    hintUploading: '업로드가 끝날 때까지 페이지를 닫거나 새로고침하지 마세요',
    hintParsing: '모든 파일이 업로드되었습니다. 파싱은 백그라운드에서 계속되므로 이 페이지를 떠나도 됩니다',
    filterAll: '전체',
    filterIssues: '미완료',
    phaseWaiting: '업로드 대기',
    phaseSaving: '저장 중…',
    phasePending: '파싱 대기',
    phaseReady: '완료',
    phaseParseFailed: '파싱 실패',
    phaseDuplicate: '동일한 파일이 이미 있습니다',
    phaseCancelled: '취소됨',
    cancel: '취소',
    cancelAll: '모두 취소',
    retry: '다시 시도',
    retryFailed: '{count}개 다시 시도',
    open: '열기',
    collapse: '접기',
    expand: '펼치기',
    close: '닫기',
    closeConfirm: '닫으면 남은 {count}개 파일의 업로드가 취소됩니다',
    closeConfirmOk: '업로드 취소',
    closeConfirmKeep: '계속 업로드',
    legend: {
      ready: '검색 가능',
      active: '처리 중',
      waiting: '대기 중',
      failed: '실패',
      duplicate: '이미 있음'
    },
    eta: {
      seconds: '{n}초',
      minutes: '{n}분',
      hours: '{n}시간'
    }
  },
  upload: {
    uploadDocument: '문서 업로드',
    uploadFolder: '폴더 업로드',
    onlineEdit: '온라인 편집',
    deleteRecord: '기록 삭제'
  },
  time: {
    today: '오늘',
    yesterday: '어제',
    last7Days: '최근 7일',
    last30Days: '최근 30일',
    lastYear: '최근 1년',
    earlier: '이전',
    pinned: '고정됨'
  },
  platform: {
    multimodalParsing: '멀티모달 문서 파싱',
    hybridSearchEngine: '하이브리드 검색 + 지식 그래프',
    ragQandA: 'ReAct 에이전트 Q&A',
    independentTenant: '독립 워크스페이스',
    fullApiAccess: '전체 API 접근',
    knowledgeBaseManagement: '지식베이스 관리',
    loginShowcase: {
      carouselLabel: '런워싱 지식 베이스 기능 예시',
      switchLabel: '기능 주제 전환',
      pause: '슬라이드와 흐름 애니메이션 일시 정지',
      play: '슬라이드와 흐름 애니메이션 재생',
      reducedMotion: '동작 줄이기 설정에 따라 자동 재생 중지',
      labels: {
        query: '질문',
        sourceHit: '원문 검색',
        citedAnswer: '인용된 답변',
        sourceMaterial: '원본 자료',
        productKnowledge: '제품 지식',
        delivery: '구축',
        customerService: '고객 지원',
        documents: '문서',
        webContent: '웹',
        existingKnowledge: '기존 지식',
        knowledgeEntry: '지식 접근',
        materialsReceived: '수집 완료',
        contentChange: '내용 변경',
        knowledgeReview: '검토',
        knowledgeUpdate: '지식 갱신',
        updateConfirmed: '업데이트 확인'
      },
      themes: {
        review: {
          title: '변화에 맞춰 지식 업데이트',
          description: '내용 변경을 검토하여 지식의 가치를 이어갑니다',
          summary: '내용 변경을 검토하고 확인한 후 관련 지식을 업데이트합니다.',
          mobile: '내용 변경 → 지식 검토 → 지식 업데이트',
          tab: '검토 및 업데이트'
        },
        intake: {
          title: '회사 자료를 한곳에',
          description: '문서, 웹 페이지, 기존 지식 플랫폼을 연결합니다',
          summary: '문서, 웹 페이지와 기존 지식을 하나의 지식 접근 창구로 모읍니다.',
          mobile: '문서 / 웹 / 기존 지식 → 통합 접근',
          tab: '자료 수집'
        },
        organization: {
          title: '흩어진 문서를 연결된 지식으로',
          description: '자료를 주제별로 정리하고 관련 지식을 연결합니다',
          summary: '자료를 제품 지식, 구축 및 납품, 고객 서비스 주제로 정리합니다.',
          mobile: '원본 자료 → 제품 / 구축 / 서비스 지식',
          tab: '지식 정리'
        },
        query: {
          title: '모든 답변에 근거를',
          description: '자연스러운 질문으로 출처가 있는 답변을 찾으세요',
          summary: '질문과 관련된 원문을 검색하고 답변과 인용을 함께 표시합니다.',
          mobile: '질문 → 원문 검색 → 인용이 있는 답변',
          tab: '답변과 출처'
        }
      }
    }
  },
  font: {
    uiFont: '인터페이스 글꼴',
    uiFontDescription: '메뉴, 본문, 버튼 등 인터페이스 대부분의 텍스트에 사용되는 글꼴입니다',
    monoFont: '코드 글꼴',
    monoFontDescription: '코드 블록, 터미널 명령, API 키, 파일 경로 등 기술 텍스트에 사용됩니다. 모든 문자가 같은 너비로 표시되어 0과 O, 1과 l을 구분할 수 있습니다.',
    selectFont: '글꼴 선택',
    sansPreview: '샘플 Sample 글꼴 — Aa Gg Oo 0123',
    monoPreview: 'const msg = \'Hello\'; // 0O1l',
    fontSize: '글꼴 크기',
    fontSizeDescription: '인터페이스 전체(텍스트, 아이콘, 간격)를 확대/축소하며 즉시 적용됩니다',
    size: {
      small: '작게',
      normal: '보통',
      large: '크게'
    },
    mono: {
      system: '시스템 기본',
      menlo: 'Menlo',
      monaco: 'Monaco',
      consolas: 'Consolas',
      cascadia: 'Cascadia Code',
      'dejavu-mono': 'DejaVu Sans Mono',
      'liberation-mono': 'Liberation Mono',
      monospace: '일반 고정폭'
    },
    sans: {
      system: '시스템 기본',
      pingfang: 'PingFang SC',
      georgia: 'Georgia (세리프)',
      yahei: 'Microsoft YaHei',
      times: 'Times New Roman (세리프)',
      'noto-cjk': 'Noto Sans CJK',
      'dejavu-serif': 'DejaVu Serif (세리프)',
      'sans-serif': '일반 산세리프'
    }
  },
  theme: {
    theme: '테마',
    themeDescription: '인터페이스의 표시 테마를 선택하세요. 시스템 설정에 따라 자동 전환을 지원합니다',
    light: '라이트',
    dark: '다크',
    system: '시스템 설정',
    selectTheme: '테마 선택'
  },
  general: {
    title: '일반 설정',
    personalSettings: '개인 설정',
    description: '언어, 외관 등 기본 옵션 설정',
    close: '설정 닫기'
  },
  language: {
    zhCN: '简体中文',
    zhTW: '번체 중국어',
    enUS: 'English',
    ruRU: 'Русский',
    koKR: '한국어',
    jaJP: '日本語',
    selectLanguage: '언어 선택',
    language: '언어',
    languageDescription: '인터페이스 표시 언어 선택',
    languageSaved: '언어 설정이 저장되었습니다'
  },
  model: {
    modelName: '모델 이름',
    defaultTag: '기본값',
    addModelInSettings: '전역 설정에서 모델 추가하기',
    loadFailed: '모델 목록 로드 실패',
    selectModelPlaceholder: '모델을 선택해주세요',
    builtinTag: '내장',
    editor: {
      legacyLocalUnavailable: 'Legacy Ollama service management is retired. The saved record is preserved. To use a local model, select API and enter its OpenAI-compatible endpoint.',
      maxOutputTokensLabel: '최대 출력 토큰',
      maxOutputTokensPlaceholder: '비워 두면 카탈로그 기본값',
      maxOutputTokensDesc: '응답 1회의 출력 상한입니다. 비워 두면 이 모델의 카탈로그 기본값을 사용합니다.',
      addTitle: '모델 추가',
      editTitle: '모델 편집',
      sectionType: '모델 유형',
      typeLabel: '모델 유형',
      sectionSource: '모델 소스',
      sectionProvider: '연결 설정',
      sectionAdvanced: '고급 옵션',
      sourceLabel: '모델 소스',
      sourceRemote: 'API',
      baseUrlLabel: 'Base URL',
      displayNameLabel: '표시 이름 (선택)',
      displayNamePlaceholder: '예: 고객지원 QA 모델',
      displayNameDesc: 'UI 표시용으로만 사용되며 실제 호출은 위의 모델 이름을 사용합니다.',
      baseUrlPlaceholder: '예: https://api.openai.com/v1',
      baseUrlPlaceholderVllm: '예: http://localhost:11434/v1',
      baseUrlPlaceholderAsr: '예: https://api.openai.com/v1',
      apiKeyOptional: 'API 키 (선택)',
      apiKeyPlaceholder: 'API 키 입력',
      customHeadersLabel: '사용자 정의 요청 헤더 (선택)',
      customHeadersDesc: '원격 모델 API 호출 시 추가되는 HTTP 헤더입니다. 기업 게이트웨이 인증이나 추적 등에 사용할 수 있으며, Authorization / Content-Type 같은 예약 헤더는 무시됩니다.',
      customHeadersAdd: '헤더 추가',
      customHeadersKeyPlaceholder: '헤더 이름',
      customHeadersValuePlaceholder: '헤더 값',
      testing: '테스트 중...',
      testConnection: '연결 테스트',
      dimensionLabel: '벡터 차원',
      dimensionPlaceholder: '예: 1536',
      dimensionOverrideLabel: '사용자 지정 출력 차원',
      dimensionOverrideDesc: '제공자 문서에서 이 모델이 dimensions 매개변수를 지원한다고 확인한 경우에만 켜세요.',
      supportsVisionLabel: '비전/멀티모달 지원',
      supportsVisionDesc: '모델의 이미지 등 멀티모달 입력 지원 여부',
      embeddingImageInputLabel: '이미지 입력',
      embeddingImageInputDesc: '모델이 이미지를 텍스트와 같은 벡터 공간에 임베딩할 수 있는지 여부. 카탈로그 모델은 자동으로 인식되며, 사용자 정의 모델은 직접 선언합니다',
      contextWindowLabel: '컨텍스트 창',
      contextWindowPlaceholder: '공급자의 전체 컨텍스트 크기를 입력',
      contextWindowDesc: '한 요청의 전체 컨텍스트 크기입니다. 고급 spec이 우선하며, 비워 두고 spec도 설정하지 않으면 알 수 없음으로 표시합니다. 공급자의 실제 한도를 입력하세요. 에이전트는 출력 토큰과 압축 여유를 확보합니다.',
      contextWindowUnknown: '알 수 없음',
      contextWindowTokens: '{count} 토큰',
      maxConcurrencyLabel: '백그라운드 동시 실행 상한',
      maxConcurrencyPlaceholder: '0이면 전역 기본값 사용',
      maxConcurrencyDesc: '문서 인덱싱/보강 등 백그라운드 작업이 이 모델을 호출하는 동시 실행 수를 제한합니다(모델별로 모든 복제본이 공유). 0 또는 비워 두면 전역 기본값을 사용하며, 대화형 채팅에는 영향을 주지 않습니다.',
      fillModelAndUrl: '먼저 모델 식별자와 Base URL을 입력해주세요',
      remoteBaseUrlRequired: 'Remote API 유형은 Base URL이 필수입니다',
      unsupportedModelType: '지원되지 않는 모델 유형',
      saveAndClose: '저장 후 닫기',
      testDraftHint: '저장하지 않고 현재 입력한 연결 설정을 테스트합니다.',
      testDraftEditHint: '현재 연결 설정과 별도로 저장한 API 키를 사용하여 테스트합니다.',
      testStale: '설정이 변경되었습니다. 다시 테스트해 주세요.',
      connectionSuccess: '연결 성공',
      connectionFailed: '연결 실패',
      connectionConfigError: '연결 실패, 설정을 확인해주세요',
      providerLabel: '프로바이더',
      providerPlaceholder: '모델 프로바이더 선택',
      providerDocs: '{provider} 모델 문서 보기',
      validation: {
        extraFieldRequired: '{name}을(를) 입력하세요',
        modelNameRequired: '모델 이름을 입력해주세요',
        modelNameEmpty: '모델 이름은 비워둘 수 없습니다',
        modelNameMax: '모델 이름은 100자를 초과할 수 없습니다',
        baseUrlRequired: 'Base URL을 입력해주세요',
        baseUrlEmpty: 'Base URL은 비워둘 수 없습니다',
        baseUrlInvalid: 'Base URL 형식이 올바르지 않습니다. 유효한 URL을 입력해주세요'
      },
      modelNamePlaceholder: {
        remote: '예: gpt-4, claude-3-opus',
        remoteVllm: '예: gpt-4-vision-preview',
        remoteAsr: '예: whisper-1'
      },
      description: {
        chat: '대화용 대규모 언어 모델 설정',
        embedding: '텍스트 벡터화용 임베딩 모델 설정',
        rerank: '결과 재정렬용 모델 설정',
        vllm: '시각 이해 및 멀티모달용 비전 언어 모델 설정',
        asr: '음성 인식 및 오디오 전사를 위한 음성 인식 모델 설정',
        default: '모델 정보 설정'
      },
      advanced: {
        toggle: '고급',
        compat: {
          label: '프로토콜 호환 재정의(JSON)',
          placeholder: '{\'{\'} "max_tokens_field": "max_tokens" {\'}\'}',
          desc: '엔드포인트 동작이 카탈로그 기본값과 다를 때만 변경할 필드만 입력합니다. 비워 두면 재정의하지 않습니다.',
          docLink: '필드 설명 보기',
          invalid: '잘못된 JSON',
          mustBeObject: 'JSON 객체여야 합니다'
        },
        legacyThinking: {
          label: '사고 파라미터 형식(레거시)',
          catalog: '카탈로그 기본값 따르기(권장)',
          none: '사고 파라미터를 보내지 않음',
          desc: '이 모델에는 이전 버전의 thinking_control 설정이 남아 있습니다. "카탈로그 기본값 따르기"를 선택하면 카탈로그가 결정합니다.'
        },
        remoteModelName: {
          label: '원격 모델 이름',
          placeholder: '비워 두면 모델 이름과 동일',
          desc: '위 모델 이름과 다를 때 실제로 공급사에 보내는 모델 ID입니다.'
        },
        api: {
          label: '프로토콜 재정의',
          auto: '자동(공급사 / URL 기준)',
          desc: '요청 프로토콜을 강제합니다. 일반적으로 변경할 필요가 없습니다.'
        }
      },
      resolved: {
        title: '실제 호출 방식',
        empty: '공급사와 모델 이름을 입력하면 이 모델이 어떻게 호출되는지 표시합니다',
        failed: '해석 실패',
        protocol: '요청 프로토콜',
        catalog: '기능 출처',
        catalogedYes: '내장 모델 프로필',
        catalogedNo: '공급사 기본값(카탈로그 미수록)',
        endpoint: '요청 엔드포인트',
        thinkingFormat: '사고 전환 전달 방식',
        thinkingLevels: '선택 가능한 사고 강도',
        noThinking: '이 모델은 사고를 지원하지 않습니다'
      },
      catalog: {
        reasoning: '추론',
        vision: '비전',
        hint: '공급사 카탈로그에서 선택하거나 사용자 지정 모델 이름을 입력할 수 있습니다.'
      }
    }
  },
  error: {
    networkError: '네트워크 오류, 연결을 확인해 주세요',
    invalidCredentials: '사용자 이름 또는 비밀번호가 올바르지 않습니다',
    tokenRefreshFailed: '토큰 갱신 실패',
    pleaseRelogin: '다시 로그인해 주세요',
    fileSizeExceeded: '파일 크기는 {size}MB를 초과할 수 없습니다!',
    unsupportedFileType: '지원하지 않는 파일 형식입니다!',
    invalidImageLink: '유효하지 않은 이미지 링크',
    tokenNotFound: '로그인 토큰을 찾을 수 없습니다. 다시 로그인해주세요',
    streamFailed: '스트림 연결 실패',
    initialization: {
      checkFailed: '검사 실패',
      testFailed: '테스트 실패'
    },
    tenant: {
      listFailed: '워크스페이스 목록 조회 실패',
      searchFailed: '워크스페이스 검색 실패',
      getApiPrincipalConfigFailed: 'API principal config 조회 실패',
      updateApiPrincipalConfigFailed: 'API principal config 업데이트 실패',
      createApiPrincipalTestTokenFailed: 'API 테스트 토큰 생성 실패',
      updateFailed: '워크스페이스 정보 업데이트 실패',
      deleteFailed: 'Failed to delete workspace'
    },
    model: {
      createFailed: '모델 생성 실패',
      getFailed: '모델 조회 실패',
      updateFailed: '모델 업데이트 실패',
      deleteFailed: '모델 삭제 실패'
    },
    auth: {
      loginFailed: '로그인 실패',
      registerFailed: '회원가입 실패',
      getUserFailed: '사용자 정보 조회 실패',
      getTenantFailed: '워크스페이스 정보 조회 실패',
      updatePreferencesFailed: '개인 설정 업데이트 실패',
      refreshTokenFailed: '토큰 갱신 실패',
      logoutFailed: '로그아웃 실패',
      validateTokenFailed: '토큰 검증 실패'
    }
  },
  mcp: {
    testResult: {
      title: '테스트 결과: {name}'
    }
  },
  system: {
    globalSettings: {
      title: '시스템 설정',
      audit: {
        action: {
          'system.setting_changed': '시스템 설정 변경',
          'system.admin_promoted': '시스템 관리자 부여',
          'system.api_key_created': '플랫폼 API 키 생성',
          'system.api_key_revoked': '플랫폼 API 키 폐기',
          'system.admin_revoked': '시스템 관리자 회수',
          'system.user_password_reset': '사용자 비밀번호 재설정',
          'system.user_created': '사용자 생성',
          'system.queue_task_retried': '실패 작업 다시 실행',
          'system.queue_task_deleted': '실패 작업 기록 삭제',
          'system.queue_task_run_now': '큐 작업 즉시 실행',
          'system.queue_task_cancelled': '큐 작업 취소',
          'system.queue_archived_purged': '실패 작업 모두 지우기'
        },
        actorRole: {
          system_admin: '시스템 관리자'
        }
      },
      listConfirm: {
        ssrf: {
          whitelist: {
            remove: {
              header: 'SSRF 화이트리스트 항목 제거',
              body: '{entry} 항목을 SSRF 화이트리스트에서 제거하시겠습니까? 제거 후에는 해당 항목이 다시 SSRF 보호 대상이 됩니다.',
              confirmBtn: '제거 확인'
            },
            add: {
              header: 'SSRF 화이트리스트 항목 추가',
              body: '{entry} 항목을 SSRF 화이트리스트에 추가하시겠습니까? 일치하는 호스트 / IP / 대역은 SSRF 보호를 우회하여 에이전트가 내부 서비스에 접근할 수 있게 됩니다. 신뢰하는 항목만 추가하세요.',
              confirmBtn: '추가 확인'
            }
          }
        }
      },
      enumLabels: {
        auth: {
          default_tenant_mode: {
            create_personal: '개인 공간 자동 생성',
            tenantless: '공간을 자동 생성하지 않음'
          },
          registration_mode: {
            self_serve: '셀프 가입 (누구나 가입 가능)',
            invite_register: '초대 가입 (유효한 링크 필요)',
            invite_only: '가입 금지 (기존 계정은 초대 수락 가능)'
          }
        }
      },
      keyDescriptions: {
        model: {
          max_concurrency: '백그라운드 작업(문서 색인/보강)이 단일 모델에 대해 갖는 기본 동시 호출 상한이며, 모델 ID 기준으로 모든 복제본이 공유합니다. 매 호출마다 실시간으로 읽고 재시작 없이 즉시 적용됩니다. 0 또는 음수는 기본 상한을 해제합니다(각 모델은 모델 관리에서 설정한 자체 상한을 계속 준수함). 백그라운드 작업에만 영향을 주며 대화형 채팅에는 영향을 주지 않습니다.'
        },
        asynq: {
          core_concurrency: '문서 및 수동 파싱의 프로세스별 보장 동시성입니다. 공유 탄력 풀도 사용할 수 있습니다. 최소 1, 서비스 재시작이 필요합니다.',
          postprocess_concurrency: '파싱 마무리 및 보강 작업 분배 전용 프로세스별 동시성입니다. 최소 1, 서비스 재시작이 필요합니다.',
          enrichment_concurrency: '요약, 이미지, 그래프 및 질문 생성의 프로세스별 보장 동시성입니다. 공유 탄력 풀도 사용할 수 있습니다. 최소 1, 서비스 재시작이 필요합니다.',
          maintenance_concurrency: '동기화, 일괄 작업 및 정리의 프로세스별 동시성으로 사용자 파이프라인과 격리됩니다. 최소 1, 서비스 재시작이 필요합니다.',
          shared_concurrency: '핵심 파싱과 콘텐츠 보강이 적체에 따라 공유하는 프로세스별 탄력 동시성입니다. 최소 1, 서비스 재시작이 필요합니다.',
          wiki_concurrency: '상위 작업과 분리된 전용 Wiki 워커 풀의 프로세스별 동시성입니다. 최소값은 1이며 적용하려면 서비스를 재시작해야 합니다.'
        },
        tenant: {
          max_owned_per_user: '슈퍼유저가 아닌 사용자가 셀프 서비스로 소유할 수 있는 최대 워크스페이스 수입니다. 워크스페이스 생성 시마다 읽으며 저장 즉시 적용됩니다. 0은 내장 기본값 10을 사용하고, 음수는 제한을 완전히 해제합니다(공개 배포에는 권장하지 않음).',
          self_service_creation_enabled: '비슈퍼유저가 공간을 직접 만들 수 있는지 설정합니다. 비활성화하면 일반 사용자는 초대로만 기존 공간에 참여할 수 있으며, 크로스 워크스페이스 슈퍼유저는 계속 만들 수 있습니다.',
          default_storage_quota_gb: '신규 워크스페이스 생성 시 기본으로 할당되는 저장 용량(GB)으로, 벡터·원본·텍스트·인덱스 등을 포함합니다. 생성 시에만 읽으며, 변경은 이후 생성되는 워크스페이스에만 적용되고 기존 워크스페이스에는 소급되지 않습니다. 0 또는 음수는 내장 기본값 10GB를 사용합니다.',
          default_storage_quota_mb: '가입 시 생성되는 개인 공간에도 적용됩니다. 양수는 GB 설정보다 우선하며 0 이하는 GB 설정을 사용합니다. 각 설정은 데이터베이스, 환경 변수, 기본값 순으로 적용되며 새 공간에만 영향을 줍니다.',
          auto_create_api_key: '신규 워크스페이스에 full_access API Key를 자동 생성하고 생성 응답에 평문 token을 반환합니다. 기존 동작에 의존하는 연동에만 사용하세요. 기본값은 비활성화입니다.',
          auto_accept_invitation: '켜면 워크스페이스 관리자가 이메일로 가입된 사용자를 초대할 때 상대가 바로 멤버가 되며, 받은편지함에서 수락할 필요가 없습니다. 끄면 「초대 발송 → 상대가 수락」 흐름을 유지합니다. 저장 즉시 적용됩니다.'
        },
        sandbox: {
          docker_enabled: 'Docker 샌드박스 백엔드를 허용할지 설정합니다. 로컬 docker.sock은 호스트 root와 같으므로 기본값은 꺼짐입니다. 시스템 관리자만 켤 수 있으며 저장 즉시 적용됩니다. 데몬 소켓을 마운트했거나 TLS가 있는 원격 tcp:// 를 쓰는 프라이빗 단일 노드에서만 켜세요.'
        },
        ssrf: {
          whitelist: 'SSRF 보호 허용 목록입니다. example.com / *.foo.com / 10.0.0.0/8 / 2001:db8::1 형식을 입력할 수 있습니다. 저장 즉시 적용됩니다. SSRF_WHITELIST_EXTRA 환경 변수는 배포자가 관리하며 여기서 덮어쓰지 않습니다.'
        },
        auth: {
          registration_mode: '가입 모드입니다. 공개 가입은 누구나 계정을 만들 수 있고, 초대 가입은 유효한 초대 링크가 필요합니다. 가입 금지 상태에서도 기존 계정은 초대를 수락할 수 있습니다. 저장 즉시 적용됩니다.',
          default_tenant_mode: '공개 가입 후 공간 초기화 정책입니다. create_personal은 개인 공간을 만들고 Owner를 부여하며, tenantless는 초대 수락 또는 직접 공간 생성 전까지 계정만 만듭니다.',
          complex_password_enabled: '복잡한 비밀번호를 사용할지 여부입니다. 활성화하면 비밀번호에 대문자, 소문자, 숫자 및 특수 문자가 포함되어야 합니다. 변경 사항은 즉시 적용되며, 새로 가입하는 사용자 또는 비밀번호를 새로 변경하거나 재설정하는 경우에만 적용됩니다. 특수 문자는 다음을 포함합니다: {specialChars}'
        }
      },
      keyLabels: {
        model: {
          max_concurrency: '모델 기본 동시 처리 상한'
        },
        asynq: {
          core_concurrency: '핵심 파싱 보장 동시성',
          postprocess_concurrency: '후처리 동시성',
          enrichment_concurrency: '콘텐츠 보강 보장 동시성',
          maintenance_concurrency: '유지 관리 동시성',
          shared_concurrency: '공유 탄력 동시성',
          wiki_concurrency: 'Wiki 워커 동시성'
        },
        tenant: {
          max_owned_per_user: '사용자당 최대 워크스페이스 수',
          self_service_creation_enabled: '사용자 공간 직접 생성 허용',
          default_storage_quota_gb: '신규 워크스페이스 기본 저장 용량 (GB)',
          default_storage_quota_mb: '신규 워크스페이스 기본 저장 용량 (MB)',
          auto_create_api_key: '신규 워크스페이스 API Key 자동 생성',
          auto_accept_invitation: '등록된 사용자 초대 시 자동 가입'
        },
        sandbox: {
          docker_enabled: 'Docker 샌드박스 사용'
        },
        ssrf: {
          whitelist: 'SSRF 보호 허용 목록'
        },
        auth: {
          registration_mode: '가입 모드',
          default_tenant_mode: '기본 공간 프로비저닝',
          complex_password_enabled: '복잡한 비밀번호 사용'
        }
      },
      runtime: {
        queueDescriptions: {
          default: '문서 파싱, 수동 재파싱',
          chat_attachment: '세션 내 업로드 첨부파일 파싱',
          postprocess: '파싱 마무리, 보강 분배',
          summary: '문서 요약, 테이블 요약',
          sync: '수동 및 예약 동기화',
          low: 'FAQ 가져오기, 일괄 재파싱, 삭제 정리',
          multimodal: '이미지 OCR, 시각 설명',
          graph: '청크 단위 그래프 추출',
          question: '청크 단위 질문 생성',
          wiki: '콘텐츠 생성, 인덱스 마무리'
        },
        queueNames: {
          default: '문서 파싱',
          chat_attachment: '대화 첨부파일 파싱',
          postprocess: '후처리 오케스트레이션',
          summary: '요약 생성',
          sync: '데이터 소스 동기화',
          low: '유지 관리 및 일괄 작업',
          multimodal: '멀티모달 처리',
          graph: '그래프 추출',
          question: '질문 생성',
          wiki: 'Wiki 처리'
        },
        poolDescriptions: {
          core: '문서 및 수동 파싱 보장 용량',
          postprocess: '파싱 마무리 및 보강 작업 분배',
          enrichment: '요약, 이미지, 그래프 및 질문 생성',
          maintenance: '데이터 소스 동기화, 일괄 작업 및 삭제 정리',
          shared: '적체에 따라 핵심 파싱 또는 보강이 공유',
          wiki: 'Wiki 콘텐츠 생성 및 전체 마무리'
        },
        pools: {
          core: '핵심 파싱',
          postprocess: '후처리 오케스트레이션',
          enrichment: '콘텐츠 보강',
          maintenance: '유지 관리 및 동기화',
          shared: '공유 탄력 풀',
          wiki: 'Wiki 풀'
        },
        tasks: {
          taskTypes: {
            documentProcess: '문서 파싱',
            manualProcess: '수동 재처리',
            temporaryDocumentProcess: '채팅 첨부 파일 파싱',
            postProcess: '문서 후처리',
            summary: '요약 생성',
            tableSummary: '표 요약 생성',
            question: '질문 생성',
            multimodal: '이미지 멀티모달 처리',
            graph: '지식 그래프 추출',
            sync: '데이터 소스 동기화',
            faqImport: 'FAQ 가져오기',
            batchReparse: '일괄 재파싱',
            batchDelete: '일괄 삭제',
            move: '문서 이동',
            indexDelete: '인덱스 삭제',
            kbClone: '지식 베이스 복제',
            kbDelete: '지식 베이스 삭제',
            wikiIngest: 'Wiki 콘텐츠 생성',
            wikiFinalize: 'Wiki 마무리'
          }
        }
      }
    }
  },
  tenant: {
    title: '워크스페이스 정보',
    currentTenant: '현재 워크스페이스',
    switchTenant: '워크스페이스 전환',
    statusActive: '활성',
    statusInactive: '비활성',
    statusSuspended: '일시 중지됨',
    statusUnknown: '알 수 없음',
    loadingInfo: '정보 로딩 중...',
    retry: '재시도',
    unknown: '알 수 없음',
    formatError: '형식 오류',
    searchPlaceholder: '워크스페이스 이름 검색 또는 워크스페이스 ID 입력...',
    noMatch: '일치하는 워크스페이스를 찾을 수 없습니다',
    switchSuccessTitle: '공간이 전환되었습니다',
    switchSuccessContent: '{name} 에 입장했습니다',
    loadTenantsFailed: '워크스페이스 목록 로드 실패',
    loading: '로딩 중...',
    api: {
      title: 'API 정보',
      userIdLabel: '사용자 ID',
      userIdDescription: '고유 사용자 식별자',
      usernameLabel: '사용자명',
      usernameDescription: '로그인 사용자명',
      createdAtLabel: '가입 시간',
      createdAtDescription: '계정이 생성된 시간'
    },
    messages: {
      fetchFailed: '워크스페이스 정보 가져오기 실패',
      networkError: '네트워크 오류, 나중에 다시 시도해주세요'
    },
    deleteDangerZone: {
      title: 'Delete this workspace',
      desc: '삭제하면 이 공간의 개인 파일, 대화 및 에이전트 설정에 접근할 수 없습니다. 계정과 공유 지식 베이스는 유지됩니다.',
      button: 'Delete workspace',
      confirmTitle: 'Delete this workspace?',
      confirmBody: '공간 “{name}”을 삭제하시겠습니까? 되돌릴 수 없습니다. 계정과 공유 지식 베이스는 유지됩니다.',
      confirmHint: 'Type the workspace name "{name}" to confirm deletion.',
      confirm: 'Delete workspace',
      nameMismatch: 'Workspace name does not match',
      success: 'Workspace deleted',
      failed: 'Failed to delete workspace'
    },
    leaveDangerZone: {
      title: '이 스페이스 나가기',
      desc: '현재 스페이스에서 멤버십을 종료합니다. 지식 베이스 및 에이전트에 접근할 수 없게 되며, 이후 초대되면 다시 참여할 수 있습니다.',
      button: '스페이스 나가기'
    },
    storage: {
      usageLabel: '저장소 사용률'
    },
    details: {
      idLabel: '워크스페이스 ID',
      nameLabel: '워크스페이스 이름',
      descriptionLabel: '워크스페이스 설명',
      businessLabel: '워크스페이스 비즈니스',
      statusLabel: '워크스페이스 상태',
      createdAtLabel: '워크스페이스 생성 시간',
      editName: '이름 수정',
      editNamePlaceholder: '새 워크스페이스 이름을 입력하세요',
      editNameConfirm: '저장',
      editNameCancel: '취소',
      editNameRequired: '워크스페이스 이름은 비어 있을 수 없습니다',
      editNameSuccess: '워크스페이스 이름이 업데이트되었습니다',
      editNameFailed: '워크스페이스 이름 업데이트 실패',
      editDescription: '설명 수정',
      editDescriptionPlaceholder: '새 워크스페이스 설명을 입력하세요',
      editDescriptionSuccess: '워크스페이스 설명이 업데이트되었습니다',
      editDescriptionFailed: '워크스페이스 설명 업데이트 실패',
      descriptionEmptyPlaceholder: '미입력'
    },
    create: {
      action: '새 워크스페이스 만들기',
      dialogTitle: '새 워크스페이스 만들기',
      dialogSubtitle: '개인 파일 공간의 기본 용량은 10 GB입니다. 모든 계정이 ContextDB 지식 베이스를 공유합니다.',
      nameLabel: '워크스페이스 이름',
      namePlaceholder: '예: 새 프로젝트',
      nameRequired: '워크스페이스 이름을 입력하세요',
      descriptionLabel: '설명(선택)',
      descriptionPlaceholder: '이 워크스페이스의 용도를 간단히 설명하세요',
      submit: '만들기',
      cancel: '취소',
      success: '워크스페이스가 생성되었습니다',
      failed: '워크스페이스 생성 실패',
      disabled: '현재 시스템에서는 초대를 통해서만 공간에 참여할 수 있으며 직접 만들 수 없습니다.'
    },
    switcher: {
      menuLabel: '워크스페이스 전환',
      currentBadge: '현재',
      homeTooltip: '기본 워크스페이스',
      empty: '현재 하나의 워크스페이스에만 속해 있습니다'
    }
  },
  chat: {
    suggestedQuestions: '이렇게 물어보세요',
    refreshSuggestedQuestions: '다른 질문',
    replaceDraftTitle: '초안을 바꾸시겠어요?',
    replaceDraftBody: '입력창의 텍스트를 이 추천 질문으로 바꿉니다.',
    historyLoadFailed: '대화 기록을 불러오지 못했습니다.',
    scrollToLatest: '최신 메시지로 이동',
    thinking: '생각 중...',
    thinkingAlt: '생각 중',
    preparingAnswer: '답변을 준비하고 있습니다…',
    connectingModelAndGeneratingAnswer: '모델에 연결하여 답변을 생성하고 있습니다…',
    modelStillResponding: '모델 응답이 평소보다 오래 걸리고 있습니다. 계속 기다리는 중…',
    deepThoughtCompleted: '심층 분석 완료',
    deepThoughtAlt: '심층 분석 완료',
    referencesTitle: '{count}개의 관련 내용 참조',
    referencesDocCount: '{count}개 문서 참조',
    referencesWebCount: '{count}개 웹 결과 참조',
    referencesDocAndWebCount: '{docCount}개 문서와 {webCount}개 웹페이지 참조',
    referencesDrawerTitle: '참고 출처',
    referencesDrawerTitleWeb: '웹 출처',
    referencesDrawerTitleDocs: '문서 출처',
    referencesDrawerTitleTools: '도구 결과',
    referencesDrawerTitleMixed: '참고 출처',
    referencesDrawerWebSection: '웹',
    referencesDrawerDocsSection: '지식베이스 문서',
    referencesDrawerToolsSection: '도구',
    referencesDrawerEmpty: '참고 출처가 없습니다',
    questionMinimapTitle: '질문',
    questionMinimapPosition: '전체 {total}턴 중 {current}턴',
    questionMinimapAriaLabel: '질문 목차',
    questionMinimapAttachmentPlaceholder: '(첨부)',
    referenceChunkCount: '{count}개 청크',
    fallbackHint: '지식 베이스에서 관련 내용을 찾지 못했습니다. 위는 모델의 직접 응답입니다.',
    truncatedHint: '모델의 응답당 출력 한도에서 답변이 잘렸습니다. 위 내용은 잘리기 전까지 생성된 부분입니다.',
    requestInfoTitle: 'Request info',
    requestInfoRequestId: 'Request ID',
    requestInfoMessageId: 'Message ID',
    requestInfoSessionId: 'Session ID',
    requestInfoUrl: 'Request',
    requestInfoSentAt: 'Sent at',
    requestInfoEmpty: 'No request info available',
    channelWeb: '웹',
    channelApi: 'API',
    channelIm: 'IM',
    chunkLabel: '청크 {index}:',
    navigateToDocument: '문서 상세 보기',
    referenceSourceBack: '전체 출처',
    referenceSourceView: '원문 보기',
    referenceSourceRelocate: '다시 찾기',
    referenceSourceLocating: '인용 위치를 찾는 중…',
    referenceSourceExact: '원문 구절을 정확히 찾았습니다',
    referenceSourcePartial: '확인된 원문을 강조했습니다. 인용 일부는 아직 일치하지 않습니다',
    referenceSourceBlock: '원문 영역을 찾았습니다. 정확한 텍스트 일치는 확인되지 않았습니다',
    referenceSourceAmbiguous: '일치하는 구절이 여러 개여서 위치를 특정할 수 없습니다',
    referenceSourceStale: '원문 또는 내용이 변경되어 정확히 찾을 수 없습니다',
    referenceSourcePrevious: '이전 인용 위치',
    referenceSourceNext: '다음 인용 위치',
    referenceSourceFoundPage: '{page}페이지에서 찾았습니다',
    referenceSourceNotFound: '인용 위치를 정확히 찾지 못해 원문을 열었습니다',
    referenceSourceOpenWeb: '원본 웹페이지에서 해당 위치 열기',
    chunkIdLabel: '청크 ID:',
    documentIdLabel: '문서 ID:',
    faqIdLabel: 'FAQ ID:',
    faqContainerIdLabel: 'Container ID:',
    faqAnswersLabel: 'Answers:',
    chunkOrdinal: '청크 {index}',
    previewContent: '내용 미리보기',
    noPlanSteps: '구체적인 단계가 제공되지 않았습니다',
    chunkIndexLabel: '청크 #{index}',
    chunkPositionLabel: '(위치: {position})',
    noRelatedChunks: '관련 청크를 찾을 수 없습니다',
    noSearchResults: '검색 결과를 찾을 수 없습니다',
    relevanceHigh: '높은 관련성',
    relevanceMedium: '중간 관련성',
    relevanceLow: '낮은 관련성',
    relevanceWeak: '약한 관련성',
    webSearchNoResults: '검색 결과를 찾을 수 없습니다',
    otherSource: '기타 출처',
    webGroupIntro: '다음 {count}개 항목의 출처:',
    graphConfigTitle: '그래프 설정',
    entityTypesLabel: '엔티티 유형:',
    relationTypesLabel: '관계 유형:',
    graphResultsHeader: '{count}개의 관련 결과 발견',
    graphNoResults: '관련 그래프 정보를 찾을 수 없습니다',
    unknownLink: '알 수 없는 링크',
    contentLengthLabel: '길이 {value}',
    notProvided: '제공되지 않음',
    errorMessageLabel: '오류 메시지',
    summaryLabel: '요약',
    rawTextLabel: '원본 텍스트',
    collapseRaw: '원문 접기',
    expandRaw: '원문 펼치기',
    noWebContent: '웹 콘텐츠를 가져올 수 없습니다',
    webFetchStatusSuccess: 'Fetched',
    webFetchStatusFailed: 'Failed',
    webFetchStatusSkipped: 'Skipped',
    webFetchErrorCode: 'Error code',
    webFetchRetryable: 'Retryable',
    webFetchContentRange: '문자 {start}–{end} / 전체 {total}',
    webFetchPartialContent: '페이지 일부',
    webFetchSummaryFailed: 'Summary failed',
    lengthChars: '{value}자',
    lengthThousands: '{value}천 자',
    lengthTenThousands: '{value}만 자',
    noDatabaseRecords: '일치하는 레코드를 찾을 수 없습니다',
    nullValuePlaceholder: '<NULL>',
    chunkCountValue: '{count}개 청크',
    documentDescriptionLabel: '문서 설명:',
    documentSourceLabel: '출처:',
    documentFileLabel: '파일 정보:',
    documentMetadataLabel: '메타데이터',
    documentInfoEmpty: '문서 정보 없음',
    positionLabel: '위치:',
    chunkPositionValue: '{index}번째 청크',
    contentLengthLabelSimple: '내용 길이:',
    fullContentLabel: '전체 내용',
    copyContent: '내용 복사',
    knowledgeBaseCount: '총 {count}개 지식베이스',
    noKnowledgeBases: '사용 가능한 지식베이스 없음',
    rawOutputLabel: '원시 출력',
    wikiWritePageTitle: 'Wiki 페이지 작성',
    wikiReplaceTextTitle: 'Wiki 텍스트 교체',
    wikiRenamePageTitle: 'Wiki 페이지 이름 변경',
    wikiDeletePageTitle: 'Wiki 페이지 삭제',
    wikiActionCreated: '생성됨',
    wikiActionUpdated: '업데이트됨',
    wikiActionRenamed: '이름 변경됨',
    wikiActionDeleted: '삭제됨',
    wikiFieldSlug: '페이지 경로',
    wikiFieldTitle: '제목',
    wikiFieldPageType: '유형',
    wikiFieldSummary: '요약',
    wikiFieldOldText: '원본 텍스트',
    wikiFieldNewText: '새 텍스트',
    wikiFieldOldSlug: '원본 경로',
    wikiFieldNewSlug: '새 경로',
    wikiFieldAffectedPages: '영향을 받는 페이지',
    wikiAffectedCount: '{count}개 페이지의 링크가 업데이트되었습니다',
    processError: '처리 오류',
    sessionExcerpt: '대화 발췌',
    noAnswerContent: '(답변 내용 없음)',
    manualSourcesHeading: '참고 출처',
    noMatchFound: '일치하는 내용을 찾을 수 없습니다',
    deleteSessionFailed: '삭제 실패, 나중에 다시 시도해주세요!',
    imageTooMany: '최대 5장까지 업로드 가능합니다',
    imageTypeSizeError: 'JPG/PNG/GIF/WEBP 형식만 지원하며, 단일 파일 10MB 이하',
    imageUploadTooltip: '이미지 업로드 (붙여넣기/드래그 지원)',
    attachmentUploadTooltip: '첨부 파일 업로드 (문서, 오디오 등)',
    attachmentWithCount: '{count}개 파일 업로드됨',
    attachmentTooMany: '최대 {max}개 파일까지 업로드 가능합니다',
    attachmentTotalTooMany: '이미지와 첨부 파일은 합쳐서 최대 {max}개까지 가능합니다',
    attachmentTooLarge: '파일 {name}이(가) {max}MB 제한을 초과합니다',
    attachmentTypeNotSupported: '지원하지 않는 파일 형식: {name}',
    attachmentUploading: '업로드 중 {progress}%',
    attachmentParsing: '분석 중',
    attachmentReady: '준비됨',
    attachmentUploadFailed: '첨부 파일 업로드 실패',
    attachmentParseFailed: '첨부 파일 분석 실패',
    attachmentStillProcessing: '첨부 파일 {name}을(를) 아직 분석 중입니다',
    memoryUsedCount: '기억 {count}개를 참고했습니다',
    memoryForget: '이 기억 삭제',
    memoryForgotten: '기억을 삭제했습니다',
    memoryForgetFailed: '삭제 실패',
    memoryHint: '이 답변이 참고한 장기 기억입니다. 삭제하면 다시 사용되지 않습니다.',
    backgroundWork: {
      count: '{count} background tasks',
      refresh: 'Refresh',
      structuredResult: 'Structured result',
      updateMessage: 'Additional task instructions',
      sendUpdate: 'Send update',
      stopRequested: 'Cancellation requested',
      actionFailed: 'Action failed. Try again.',
      cancelFailed: 'Cancellation failed. Try again.',
      stop: '중지',
      loading: '출력을 불러오는 중…',
      unavailable: '출력을 볼 수 없습니다',
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
      tooltip: '여기로 되돌리기',
      confirmTitle: '여기로 되돌릴까요?',
      confirmBody: '이 메시지 이후의 대화를 삭제합니다. 질문에서 되돌리면 해당 질문도 지워지고 입력창에 다시 채워집니다. 체크포인트가 있으면 작업 영역도 되돌립니다. 이 작업은 취소할 수 없습니다.',
      confirmButton: '되돌리기',
      cancelButton: '취소',
      success: '되돌렸습니다',
      reloadFailed: '대화는 되돌렸지만 기록을 다시 불러오지 못했습니다. 이전 메시지가 없으면 새로고침하세요',
      failed: '되돌리기에 실패했습니다. 다시 시도하세요',
      skipped: '대화는 되돌렸지만 작업 영역은 변경하지 않았습니다',
      skipNoSandbox: '대화는 되돌렸지만 작업 영역은 변경하지 않았습니다(샌드박스가 없음)',
      skipNoCheckpoint: '대화는 되돌렸지만 작업 영역은 변경하지 않았습니다(되돌릴 체크포인트가 없음)'
    },
    sandbox: {
      panelTitle: '샌드박스',
      tabArtifacts: '파일',
      tabTerminal: '터미널',
      tabDesktop: '데스크톱',
      artifactsEmpty: '이 대화에서 생성된 파일이 없습니다',
      artifactScope: '파일 범위',
      artifactsCurrent: '이번 응답',
      artifactsAll: '전체',
      artifactsSearch: '파일 이름 검색',
      artifactsNoMatches: '일치하는 파일이 없습니다',
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
      paused: '이 대화의 샌드박스가 일시 중지되었습니다. 터미널을 시작하면 다시 시작됩니다.',
      stopped: '이 대화의 샌드박스가 실행 중이 아닙니다. 중지되었거나 오랫동안 유휴 상태여서 회수되었을 수 있습니다. 터미널을 시작하면 다시 시작되며, 이미 회수된 경우 새 샌드박스가 만들어지고 이전 파일과 설치한 소프트웨어는 유지되지 않습니다.',
      start: '터미널 시작',
      connecting: '샌드박스에 연결하는 중…',
      needsProvision: '이 대화에는 실행 중인 샌드박스가 없습니다. 생성하고 시작하면 새 샌드박스가 만들어지며 워크스페이스 설정에 따라 요금이 부과됩니다.',
      createAndStart: '생성 후 시작',
      noSandbox: '아직 샌드박스가 없고 현재 에이전트에 샌드박스 백엔드가 구성되지 않아 만들 위치를 정할 수 없습니다. 샌드박스가 구성된 에이전트로 전환하거나 코드 실행이 필요한 메시지를 보내세요.',
      unsupported: '현재 샌드박스 백엔드는 대화형 터미널을 지원하지 않습니다',
      disconnected: '연결이 끊어졌습니다',
      retry: '다시 연결',
      sessionEnded: '터미널 세션이 종료되었습니다',
      idleDisconnected: '터미널이 유휴 상태로 연결이 끊어졌습니다. 샌드박스는 TTL에 따라 일시 중지됩니다. 다시 연결할 수 있습니다.',
      idleDisconnectedNewShell: '터미널이 유휴 상태로 연결이 끊어져 셸이 종료되었습니다(nohup으로 시작한 백그라운드 작업은 영향을 받지 않습니다). 다시 연결하면 새 셸이 열립니다.',
      disconnectedNewShell: '연결이 끊어져 터미널의 셸이 종료되었습니다(nohup으로 시작한 백그라운드 작업은 영향을 받지 않습니다). 다시 연결하면 새 셸이 열립니다.',
      authRevoked: '로그인 상태가 더 이상 유효하지 않아 터미널 연결이 끊어졌습니다. 다시 로그인한 뒤 재연결하세요.'
    },
    conversationTime: {
      today: '오늘 {time}',
      yesterday: '어제 {time}',
      thisYear: '{month}월 {day}일 {time}',
      otherYear: '{year}년 {month}월 {day}일 {time}'
    }
  },
  knowledgeEditor: {
    titleCreate: '지식베이스 생성',
    titleEdit: '지식베이스 설정',
    advanced: {
      title: '고급 설정',
      description: '질문 생성, 멀티모달 등 고급 기능 설정',
      multimodal: {
        label: '멀티모달 기능',
        description: '이미지 등 멀티모달 콘텐츠 이해 기능 활성화',
        vllmLabel: 'VLLM 비전 모델',
        vllmDescription: '멀티모달 이해를 위한 비전 언어 모델 (필수)',
        vllmPlaceholder: 'VLLM 모델을 선택해주세요 (필수)',
        descriptionLanguageLabel: '이미지 설명 언어',
        descriptionLanguageDescription: '비워 두면 문서 언어를 따릅니다',
        descriptionLanguageAuto: '문서 언어 자동 사용',
        customInstructionsLabel: '이미지 처리 지침',
        customInstructionsDescription: 'OCR 및 Markdown 형식은 유지하면서 시각적 우선순위를 추가합니다',
        customInstructionsPlaceholder: '예: 명판, 모델 번호, 경고 코드 및 표 단위를 중점적으로 인식…',
        imageVectorLabel: '이미지 벡터 검색',
        imageVectorDescription: '켜면 이미지 설명을 생성한 뒤 임베딩 모델로 이미지 자체도 인코딩하여, 설명에 없는 내용으로도 이미지를 검색할 수 있습니다. 이미지 입력을 지원하는 임베딩 모델이 필요하며, 이미지마다 임베딩 호출이 한 번 늘고 벡터 검색 후보 범위도 넓어집니다. 이후 수집하거나 다시 파싱한 문서에만 적용되며, 스캔 PDF 페이지는 제외됩니다',
        imageVectorModelUnsupported: '현재 임베딩 모델은 이미지 입력을 선언하지 않아 이미지 벡터가 생성되거나 검색되지 않습니다',
        imageAttrsSchemaLabel: '관찰 가능한 이미지 속성',
        imageAttrsSchemaDescription: '모델은 아래 속성(백엔드 레지스트리 정의)을 관찰해 OCR 정책을 결정합니다',
        imagePipelineSectionLabel: '이미지 분석 방식',
        imagePipelineSectionDescription: '멀티모달 분석이 켜져 있으면 이미지의 분석 방식을 필요에 따라 선택할 수 있습니다.',
        imagePipelineLabel: '분석 방식',
        advancedSettingsLabel: '고급 설정',
        notesLabel: '추가 설명',
        imagePipelinePlaceholder: '분석 방식 선택',
        imagePipelineLoading: '파이프라인을 불러오는 중…',
        imagePipelineLoadError: '파이프라인을 불러오지 못했습니다',
        imagePipelineValidateError: '현재 설정을 검증할 수 없습니다. 저장 시 백엔드가 다시 검사합니다.',
        imageAttrsOcrConditions: '관찰된 속성 조건에 따라 OCR 실행',
        imageAttrsOcrConditionsDesc: '관찰된 속성이 아래 조건을 충족하면 해당 이미지에 OCR을 실행합니다',
        imagePipelineKbNote: '기본값은 지식베이스 설정을 따르며 이번 작업에 맞게 조정할 수 있습니다'
      },
      tableMetadataInstructions: {
        label: '테이블 메타데이터 지침',
        description: 'CSV/Excel 요약에 비즈니스 배경과 필드 의미를 추가합니다',
        placeholder: '예: 판매 주문 테이블이며 금액 단위와 내부 상태 코드를 설명…'
      },
      autoTag: {
        label: '자동 태그 연결',
        description: '문서 파싱 후 현재 지식베이스의 기존 태그 중 적합한 태그를 연결합니다. 태그를 생성하거나 삭제하지 않으며 모델 호출이 한 번 추가됩니다.',
        modelLabel: '분류 모델',
        modelDescription: '비워 두면 지식베이스 요약 모델을 사용합니다.',
        modelPlaceholder: '분류 모델 선택',
        maxTagsLabel: '문서당 최대 태그 수',
        maxTagsDescription: '문서마다 기존 태그 1-10개를 자동 연결합니다.',
        skipIfTaggedLabel: '태그가 있는 문서 건너뛰기',
        skipIfTaggedDescription: '활성화하면 업로드 시 수동으로 태그를 지정한 문서에는 자동 태그를 추가하지 않아 사용자의 분류 의도를 유지합니다.'
      },
      profile: {
        label: '지식베이스 설명 자동 생성',
        description: '문서 추가·삭제·요약 갱신 후 문서 프로필 집계에서 설명을 자동 생성합니다. 집계 자체는 모델을 호출하지 않으며, 집계 결과가 바뀔 때만 작은 모델 호출을 한 번 수행합니다.',
        modelLabel: '생성 모델',
        modelDescription: '비워 두면 지식베이스 요약 모델을 사용합니다.',
        modelPlaceholder: '생성 모델 선택',
        instructionsLabel: '설명 생성 요구사항',
        instructionsDescription: '대상 독자, 유지할 용어, 문체 등을 보충합니다. 출력 형식은 고정됩니다.',
        instructionsPlaceholder: '예: 고객지원 담당자 대상, 제품군을 쉬운 말로 설명하고 모델 번호는 유지…'
      },
      questionGeneration: {
        modelLabel: '질문 생성 모델',
        modelDescription: '비워 두면 지식 베이스 요약 모델을 사용합니다.',
        modelPlaceholder: '질문 생성 모델 선택',
        label: 'AI 질문 생성',
        description: '문서 파싱 시 대규모 모델을 호출하여 각 청크에 대한 관련 질문을 생성하여 검색 재현율을 향상시킵니다. 활성화하면 문서 파싱 시간이 증가합니다.',
        countLabel: '생성 질문 수',
        countDescription: '각 문서 청크에서 생성할 질문 수 (1-10)',
        instructionsLabel: '질문 생성 지침',
        instructionsDescription: '안정적인 출력 형식을 유지하면서 대상, 상황 및 표현 방식을 지정합니다',
        instructionsPlaceholder: '예: 시험 문제 형식을 피하고 자연스러운 고객 지원 질문을 생성…'
      }
    },
    asr: {
      title: '오디오 음성 인식',
      description: 'ASR(음성-텍스트)을 설정합니다. 활성화 시 오디오 파일을 업로드해 텍스트로 전사할 수 있습니다(mp3, wav, m4a, flac, ogg 등). 동영상 업로드는 지원하지 않습니다.',
      label: '오디오 음성 인식 사용',
      desc: '활성화하면 오디오를 지식베이스에 업로드할 수 있으며, 음성이 텍스트로 전사되어 파싱·검색에 사용됩니다',
      modelLabel: 'ASR 모델',
      modelDescription: '오디오의 음성을 텍스트로 전사하는 모델 (예: OpenAI Whisper)',
      modelPlaceholder: 'ASR 모델을 선택해주세요',
      languageLabel: '오디오 언어 힌트',
      languageDescription: '선택 사항입니다. 기본 언어를 지정하면 일부 ASR 모델의 인식이 향상되며, 비워 두면 자동 감지합니다.',
      languagePlaceholder: '예: zh, en; 비워 두면 자동 감지'
    },
    multimodal: {
      title: '이미지 처리 설정',
      description: '이미지 콘텐츠 이해 기능을 설정하여 이미지 등 비텍스트 콘텐츠의 파싱 및 검색을 지원합니다'
    },
    chunking: {
      title: '청크 설정',
      description: '업로드된 문서가 임베딩되기 전에 분할되는 방식을 제어합니다. 대부분의 경우 기본값으로 충분합니다.',
      sizeLabel: '청크 크기',
      sizeDescription: '청크당 최대 문자 수 (100-4000). 기본값 512 ≈ 영어 100-130 토큰. FAQ는 200-400, 서술형 문서는 1000-2000.',
      characters: '문자',
      overlapLabel: '청크 중복',
      overlapDescription: '인접 청크 간 공유 문자 수 (0-500). 기본값 80 ≈ 청크 크기의 15% — 현재 연구 권장값. FAQ/구조화 데이터는 0, 긴 서술은 150-200.',
      separatorsLabel: '구분자',
      separatorsDescription: '분할 시 우선적으로 사용되는 문자/문자열. 우선순위가 높은 구분자를 먼저 시도; 기본 순서는 단락 → 문장 → 구두점.',
      separatorsPlaceholder: '구분자 선택 또는 사용자 정의',
      parentChildLabel: '부모-자식 청킹',
      parentChildDescription: '2단계 청킹: 작은 자식 청크는 벡터 매칭(정확한 히트), 큰 부모 청크는 LLM에 반환(풍부한 컨텍스트). 긴 문서(>10페이지)에 권장; 짧은 FAQ는 비활성화하여 저장 공간 절약.',
      parentChunkSizeLabel: '부모 청크 크기',
      parentChunkSizeDescription: 'LLM에 반환되는 컨텍스트 청크 크기 (512-8192). 기본값 4096 ≈ 1000 영어 토큰, 모든 현대 LLM 컨텍스트에 적합.',
      childChunkSizeLabel: '자식 청크 크기',
      childChunkSizeDescription: '벡터 매칭에 사용되는 임베딩 청크 크기 (64-2048). 기본값 384 ≈ 80 토큰 — sentence-transformer / BGE 임베더의 최적점.',
      strategyLabel: '청킹 전략',
      strategyDescription: '문서를 청크로 분할하는 방법을 선택합니다. 자동 모드는 문서를 프로파일링하여 최적의 전략을 선택합니다.',
      strategyPlaceholder: '청킹 전략 선택 (비워 두면 길이로 분할)',
      overlapWarning: '오버랩이 청크 크기에 비해 큽니다 — 청크가 대부분의 콘텐츠를 공유합니다.',
      advancedLabel: '고급 옵션',
      tokenLimitLabel: '청크당 토큰 제한',
      tokenLimitDescription: '청크당 토큰 하드 제한 (0-8192). 0 = 끄기 (문자 크기만). 임베딩 모델의 토큰 제한이 작을 때 활성화: MiniLM (256 tok)은 200, BGE/Cohere (512 tok)는 400. 현대 임베더(OpenAI, Voyage, Jina-v3)는 >2000 토큰 지원 — 0으로 두세요.',
      languagesLabel: '언어 힌트',
      languagesDescription: '휴리스틱 패턴을 선택한 언어(DE/EN/ZH)로만 제한합니다. 비어 있음 = 샘플에서 자동 감지. 동질적인 코퍼스는 명시적으로 설정하여 언어 간 오탐 방지.',
      languagesPlaceholder: '자동 감지',
      debug: {
        toggle: '청킹 결과 미리보기',
        toggleHint: '재업로드 없이 샘플 텍스트에 대해 청커 실행',
        sampleLabel: '샘플 텍스트',
        samplePlaceholder: '현재 구성으로 어떻게 청크되는지 보려면 Markdown / 일반 텍스트 스니펫을 붙여넣으세요…',
        presetLabel: '샘플 불러오기:',
        runButton: '미리보기 실행',
        loading: '샘플에 대해 청커 실행 중…',
        errorPrefix: '미리보기 실패',
        selectedTier: '선택된 전략',
        rejected: '거부된 계층',
        contextHeader: '컨텍스트 헤더',
        fallbackWarning: '전략 체인이 모두 실패함 — 현재 설정으로는 콘텐츠를 지능적으로 분할할 수 없음',
        stats: {
          chunks: '청크',
          truncated: '잘림; 총 {total}'
        },
        profile: {
          lines: '줄',
          chars: '문자',
          headings: 'Markdown 제목',
          pageBreaks: '페이지 구분',
          chapterMarkers: '챕터 마커',
          languages: '언어'
        },
        samples: {
          markdown: 'Markdown 문서',
          faq: 'FAQ 목록',
          chapter: 'PDF 챕터',
          plain: '일반 텍스트'
        }
      },
      languageOptions: {
        de: '독일어',
        en: '영어',
        zh: '중국어'
      },
      strategies: {
        legacy: {
          label: '길이 기준',
          tooltip: '구조를 무시하고 문자 수와 구분자로만 재귀 분할합니다 — 원래 동작. 위 전략들이 콘텐츠에서 잘못 작동할 때 사용하세요.'
        },
        heuristic: {
          label: '구조 인식',
          tooltip: '페이지 구분자, 번호 매겨진 섹션, 다국어 챕터 마커(DE/EN/ZH), 대문자 제목 등 구조적 신호를 감지하여 분할합니다. Markdown 헤딩이 없는 PDF/스캔본에 적합합니다.'
        },
        heading: {
          label: '헤딩 기준',
          tooltip: 'Markdown 헤딩(#, ##, ###) 경계에서 분할하며 각 청크에 헤딩 경로가 부착됩니다. 잘 구조화된 Markdown 문서에 적합합니다.'
        },
        auto: {
          label: '자동',
          tooltip: '문서 프로파일러가 콘텐츠 구조에 따라 「헤딩 기준」, 「구조 인식」, 「길이 기준」 분할 중 하나를 자동 선택합니다.'
        }
      },
      separators: {
        doubleNewline: '이중 줄바꿈 (\\n\\n)',
        singleNewline: '단일 줄바꿈 (\\n)',
        periodCn: '중국어 마침표 (。)',
        exclamationCn: '느낌표 (！)',
        questionCn: '물음표 (？)',
        semicolonCn: '중국어 세미콜론 (；)',
        semicolonEn: '영어 세미콜론 (;)',
        space: '공백 ( )'
      }
    },
    models: {
      title: '모델 설정',
      description: '지식베이스에 적합한 AI 모델 선택',
      llmLabel: 'LLM 대규모 언어 모델',
      llmDesc: '요약 및 개요를 위한 대규모 언어 모델',
      llmPlaceholder: 'LLM 모델을 선택해주세요 (선택)',
      embeddingLabel: 'Embedding 임베딩 모델',
      embeddingDesc: '텍스트 벡터화를 위한 임베딩 모델',
      embeddingPlaceholder: 'Embedding 모델을 선택해주세요',
      embeddingLocked: '지식베이스에 이미 파일이 있어 Embedding 모델을 변경할 수 없습니다',
      embeddingOptional: '(선택)',
      embeddingWikiOptionalDesc: '선택 사항입니다. 설정하면 Wiki 디렉터리 분류의 유사도 매칭에 사용되어 새 페이지가 기존 폴더를 더 잘 재사용합니다. 설정하지 않으면 전체 디렉터리 트리를 기준으로 분류합니다.'
    },
    faqImport: {
      title: 'FAQ 일괄 가져오기'
    },
    faq: {
      title: 'Q&A',
      description: 'FAQ 지식베이스의 인덱스 전략 및 Q&A 구성 방식 설정',
      indexModeLabel: '인덱스 방식',
      indexModeDescription: '질문만 인덱싱하면 정확도가 향상되고, Q&A를 인덱싱하면 재현율이 향상됩니다',
      questionIndexModeLabel: '질문 인덱스 방식',
      questionIndexModeDescription: '병합 인덱스: 표준 질문과 유사 질문을 병합 인덱싱; 개별 인덱스: 표준 질문과 각 유사 질문을 독립적으로 인덱싱하여 더 정확하게 검색하지만 더 많은 저장 스페이스가 필요합니다',
      entryGuide: 'FAQ 항목은 표준 질문, 유사 질문, 반례 및 여러 답변으로 구성됩니다. 지식베이스 세부 정보에서 일괄 가져오기 및 편집할 수 있습니다.',
      modes: {
        questionOnly: '표준 질문/유사 질문만',
        questionAnswer: '표준 질문 + 답변',
        combined: '병합 인덱스',
        separate: '개별 인덱스'
      }
    },
    document: {
      title: '문서'
    },
    messages: {
      loadModelsFailed: '모델 목록 로드 실패',
      loadDataFailed: '지식베이스 데이터 로드 실패',
      notFound: '지식베이스가 존재하지 않습니다',
      nameRequired: '지식베이스 이름을 입력해주세요',
      summaryRequired: 'Summary 모델을 선택해주세요',
      multimodalInvalid: '멀티모달 설정 검증 실패',
      createSuccess: '지식베이스 생성 성공',
      createFailed: '지식베이스 생성 실패',
      missingId: '지식베이스 ID가 없습니다',
      buildDataFailed: '데이터 구축 실패',
      updateSuccess: '설정 저장 성공',
      indexModeRequired: 'FAQ 인덱스 방식을 선택해주세요',
      storageChangeConfirm: '지식베이스에 파일이 있습니다. 스토리지 엔진을 변경하면 이전 파일에 접근할 수 없게 될 수 있습니다. 계속하시겠습니까?'
    },
    share: {
      description: '스페이스 구성원이 접근하고 사용할 수 있도록 지식베이스를 스페이스에 공유합니다.',
      hintTitle: '공유 안내',
      addShare: '공유',
      unshareConfirm: '"{name}" 공유를 취소하시겠습니까?',
      tip1: '공유 후 스페이스 구성원은 설정된 권한에 따라 이 지식베이스에 액세스하게 됩니다.',
      tip2: '편집 가능한 권한을 통해 구성원은 지식베이스 콘텐츠를 수정할 수 있으며, 읽기 전용 권한은 검색 및 Q&A만 허용합니다.'
    },
    postCreateHint: {
      title: '생성 완료',
      footer: '설정을 계속 조정하고 공유·데이터 소스를 구성한 뒤 "저장 후 닫기"를 클릭하세요.',
      followUpDesc: '왼쪽에서 데이터 소스를 구성하거나 "공유 관리"에서 스페이스에 게시할 수 있습니다'
    },
    footer: {
      instantEffect: '이 페이지의 변경 사항은 즉시 적용되며 저장할 필요가 없습니다'
    },
    buttons: {
      create: '지식베이스 생성',
      saveAndClose: '저장 후 닫기'
    },
    wikiBrowser: {
      viewInGraph: '그래프에서 보기',
      filterSummary: '요약',
      filterEntity: '엔티티',
      filterConcept: '개념',
      filterSynthesis: '종합',
      filterComparison: '비교',
      version: 'v{ver}',
      gallery: {
        attr: {
          builtin_caption: '설명',
          builtin_caption_description: '모델이 생성한 이미지 설명',
          builtin_ocr_text: 'OCR 텍스트',
          builtin_ocr_text_description: 'OCR 로 이미지에서 추출한 텍스트',
          builtin_page: '문서 페이지',
          builtin_page_description: '원본 문서별로 묶어 PDF 페이지순으로 정렬합니다. 페이지를 알 수 없는 이미지는 각 문서의 마지막에 표시됩니다.',
          builtin_created_at: '생성 시간',
          builtin_created_at_description: '소유 문서 조각이 생성된 시각',
          builtin_updated_at: '수정 시간',
          builtin_updated_at_description: '소유 문서 조각이 마지막으로 수정된 시각',
          builtin_is_enabled: '활성 상태',
          builtin_is_enabled_description: '소유 문서 조각이 검색에 참여하는지 여부',
          builtin_is_enabled_value_true: '활성화',
          builtin_is_enabled_value_false: '비활성화'
        }
      }
    },
    indexing: {
      title: '인덱싱 전략',
      description: '문서 업로드 후 처리 파이프라인을 구성합니다. 각 인덱싱 방식을 독립적으로 켜거나 끌 수 있습니다',
      searchTitle: 'RAG 검색',
      searchDesc: '문서를 청크 분할, 벡터화, 키워드 인덱싱하여 하이브리드 검색을 지원합니다',
      wikiTitle: 'Wiki 지식베이스',
      wikiDesc: '상호 연결된 Wiki 지식 페이지를 자동 생성하여 구조화된 지식 체계를 구축합니다',
      atLeastOne: '최소 하나의 인덱싱 전략을 활성화해야 합니다',
      embeddingRequired: 'RAG 검색에는 Embedding 모델 설정이 필요합니다',
      lockedTip: '지식베이스에 콘텐츠가 있어 인덱싱 전략을 변경할 수 없습니다. 변경하려면 먼저 지식베이스를 비우세요.',
      rebuildConfirmTitle: '인덱스 재구축',
      rebuildConfirmBody: '인덱싱 전략이 변경되었습니다. 기존 {count}개 문서를 재처리하시겠습니까? 시간이 다소 걸릴 수 있습니다.',
      rebuildSuccess: '재구축 작업이 제출되었습니다. 총 {count}개 문서',
      rebuildSkip: '데이터 소스에서 나중에 수동으로 재구축할 수 있습니다'
    },
    wiki: {
      title: 'Wiki 설정',
      synthesisModelLabel: '합성 모델',
      synthesisModelPlaceholder: 'Wiki 생성에 사용할 LLM 모델을 선택하세요',
      synthesisModelTip: '설정하지 않으면 요약 모델로 대체됩니다',
      autoGenerateLabel: 'Wiki 페이지 자동 생성',
      autoGenerateTip: '사용하지 않아도 Wiki 페이지를 탐색하고 수동으로 편집할 수 있지만, 문서 처리 중 LLM으로 페이지를 생성하거나 업데이트하지 않습니다',
      extractionGranularityLabel: '추출 세분화 수준',
      contentInstructionsLabel: 'Wiki 콘텐츠 생성 지침',
      contentInstructionsTip: '요약, 페이지 및 인덱스의 강조점과 문체를 지정합니다. 인용 및 병합 규칙은 시스템에서 유지합니다.',
      contentInstructionsPlaceholder: '예: 책임자, 일정 및 위험을 우선적으로 표시…',
      extractionInstructionsLabel: 'Wiki 추출 중점',
      extractionInstructionsTip: '시스템 JSON 및 인용 규칙을 바꾸지 않고 우선할 엔티티와 개념을 지정합니다.',
      extractionInstructionsPlaceholder: '예: 제품, 버전, 조직, 담당자 및 핵심 기술 개념을 우선…',
      extractionGranularityTip: '문서당 추출되는 Wiki 엔티티/개념 수를 제어합니다. 세밀할수록 인덱스가 간결하고, 거칠수록 포괄적입니다',
      granularityFocused: '집중',
      granularityStandard: '표준',
      granularityExhaustive: '상세',
      granularityFocusedHint: '문서의 주요 주체만 추출합니다 (예: 이력서 → 인물과 프로젝트). 가장 깔끔하지만 부수 엔티티는 누락될 수 있습니다.',
      granularityStandardHint: '주요 주체 + 상세히 논의된 부수 엔티티/개념. 지나가듯 언급된 용어는 생략합니다. 권장 기본값입니다.',
      granularityExhaustiveHint: '스쳐 지나가는 기술 스택 언급을 포함해 명명된 모든 엔티티와 개념을 추출합니다. KB를 용어집으로 사용할 때 적합합니다.'
    },
    basic: {
      title: '기본 정보',
      description: '지식베이스의 이름과 설명 정보 설정',
      kbId: '지식베이스 ID',
      kbIdDesc: 'API 연동에서 이 ID로 지식베이스를 지정할 수 있습니다',
      typeLabel: '지식베이스 유형',
      typeDocument: '문서',
      typeFAQ: 'Q&A',
      typeDescription: 'FAQ 유형은 구조화된 Q&A 데이터에 적합합니다. 문서 유형은 파일 파싱과 청킹을 지원합니다. Wiki 유형은 LLM을 통해 상호 연결된 지식 페이지를 자동으로 구축합니다.',
      nameLabel: '지식베이스 이름',
      namePlaceholder: '지식베이스 이름을 입력해주세요',
      descriptionLabel: '지식베이스 설명',
      descriptionPlaceholder: '지식베이스 설명을 입력해주세요 (선택)',
      profile: {
        title: 'AI 생성 설명',
        hint: '문서 프로필 집계에서 생성됩니다. 위의 수동 설명을 덮어쓰지 않으며, 에이전트는 두 설명을 함께 읽어 질문이 이 지식베이스에 속하는지 판단합니다.',
        empty: '아직 생성되지 않았습니다. 문서를 업로드하고 요약이 완료된 뒤 아래 버튼으로 생성하세요.',
        noDocuments: '이 지식베이스에 파싱이 완료된 문서가 아직 없습니다.',
        questions: '대표 질문',
        generate: 'AI 설명 생성',
        regenerate: '다시 생성',
        adopt: '설명으로 사용',
        generated: 'AI 설명이 생성되었습니다',
        generateFailed: 'AI 설명 생성에 실패했습니다',
        adopted: '설명란에 복사했습니다. 저장하면 적용됩니다',
        failed: '마지막 생성 실패: {error}',
        generatedAt: '{time} 생성 · 문서 {count}개 기준'
      }
    },
    errors: {
      vectorStoreBindingInvalid: '선택한 벡터 스토어를 사용할 수 없습니다. 다른 스토어를 선택하거나 시스템 기본값을 사용하세요.',
      vectorStoreUnavailable: '선택한 벡터 스토어가 현재 사용할 수 없는 상태입니다. 설정 → 벡터 스토어에서 연결 상태를 확인하세요.'
    },
    sidebar: {
      basic: '기본 정보',
      models: '모델 설정',
      vectorStore: '벡터 스토어',
      chunking: '청크 설정',
      storage: '스토리지 엔진',
      advanced: '고급 설정',
      faq: 'FAQ 설정',
      graph: '지식 그래프',
      multimodal: '이미지 처리',
      asr: '오디오',
      datasource: '데이터 소스',
      share: '공유관리',
      activity: '활동 기록'
    },
    navGroups: {
      basic: '기본',
      processing: '인덱싱 및 파싱',
      data: '스토리지 및 데이터',
      integration: '게시 및 통합',
      management: '관리 및 감사'
    },
    activity: {
      title: '활동 기록',
      description: '이 지식 베이스의 주요 변경 사항과 백그라운드 작업 시작 기록입니다. 보존 기간은 감사 로그 정책을 따릅니다.',
      allOutcomes: '모든 결과',
      allActions: '모든 작업',
      refresh: '새로고침',
      retry: '다시 시도',
      empty: '아직 활동 기록이 없습니다',
      emptyFiltered: '일치하는 활동 기록이 없습니다',
      clearFilters: '필터 지우기',
      loadingMore: '불러오는 중…',
      end: '이전 기록이 없습니다',
      loadFailed: '활동 기록을 불러오지 못했습니다',
      systemActor: '시스템',
      actorWithAPIKey: '{actor} · API Key · {name}',
      actorAPIKey: 'API Key · {name}',
      viaAssistant: 'Xiaozhi 어시스턴트 경유',
      knowledgeBase: '지식 베이스',
      countItems: '{count}개 항목',
      titleWithCount: '{title} 외 {count}개',
      importSummary: '성공 {success} / 실패 {failed} / 건너뜀 {skipped}',
      detailValues: {
        user: '사용자 시작',
        manual: '수동',
        schedule: '예약',
        system: '시스템',
        pending: '대기 중',
        completed: '완료',
        partial: '일부 완료',
        canceled: '취소됨',
        failed: '실패',
        enqueue: '작업 제출',
        reuse_vectors: '벡터 재사용',
        reparse: '재분석',
        viewer: '읽기 전용',
        editor: '편집 가능',
        admin: '관리',
        append: '추가',
        replace: '덮어쓰기'
      },
      outcomes: {
        accepted: '접수됨',
        success: '성공',
        failed: '실패',
        partial: '일부 완료',
        canceled: '취소됨',
        denied: '거부됨'
      },
      actions: {
        'kb.created': '지식 베이스 생성',
        'kb.updated': '지식 베이스 업데이트',
        'kb.deleted': '지식 베이스 삭제',
        'kb.duplicated': '지식 베이스 복제',
        'kb.clone_started': '복제 시작',
        'kb.clone_completed': '복제 완료',
        'kb.clone_failed': '복제 실패',
        'knowledge.created': '지식 추가',
        'knowledge.updated': '지식 업데이트',
        'knowledge.deleted': '지식 삭제',
        'knowledge.batch_deleted': '지식 일괄 삭제',
        'knowledge.reparse_started': '재분석 시작',
        'knowledge.parse_canceled': '분석 취소',
        'knowledge.move_started': '지식 이동 시작',
        'knowledge.move_completed': '지식 이동 완료',
        'knowledge.move_failed': '지식 이동 실패',
        'tag.created': '태그 생성',
        'tag.updated': '태그 업데이트',
        'tag.deleted': '태그 삭제',
        'datasource.created': '데이터 소스 생성',
        'datasource.updated': '데이터 소스 업데이트',
        'datasource.deleted': '데이터 소스 삭제',
        'datasource.sync_started': '데이터 소스 동기화 시작',
        'datasource.sync_completed': '데이터 소스 동기화 완료',
        'datasource.sync_failed': '데이터 소스 동기화 실패',
        'datasource.paused': '데이터 소스 일시 중지',
        'datasource.resumed': '데이터 소스 재개',
        'kb.share_added': '공유 추가',
        'kb.share_permission_changed': '공유 권한 변경',
        'kb.share_removed': '공유 제거',
        'wiki.content_changed': 'Wiki 콘텐츠 업데이트',
        'faq.import_started': 'FAQ 가져오기 시작',
        'faq.import_completed': 'FAQ 가져오기 완료',
        'faq.import_failed': 'FAQ 가져오기 실패'
      },
      detailFields: {
        task_id: '작업 ID',
        trigger: '트리거',
        processing_status: '처리 상태',
        source_kb_id: '소스 지식 베이스 ID',
        target_kb_id: '대상 지식 베이스 ID',
        sync_log_id: '동기화 로그 ID',
        mode: '모드',
        attempt: '처리 시도',
        count: '항목 수',
        total: '전체',
        processed: '처리됨',
        failed: '실패',
        skipped: '건너뜀',
        failure_stage: '실패 단계'
      },
      targets: {
        knowledge_base: '지식 베이스',
        knowledge: '지식',
        faq_entry: 'FAQ 항목',
        knowledge_tag: '태그',
        data_source: '데이터 소스',
        knowledge_base_share: '공유',
        knowledge_move: '지식 이동',
        wiki: 'Wiki'
      },
      drawer: {
        sectionSummary: '요약',
        sectionIdentifiers: '식별자',
        sectionTask: '작업 정보',
        targetChange: '변경 내용'
      },
      expanded: {
        targetType: '대상 유형',
        targetId: '대상 ID',
        actorId: '시작자 ID',
        apiKeyName: 'API 키 이름',
        apiKeyId: 'API 키 ID',
        agentSessionId: '어시스턴트 대화 ID',
        agentOperation: '어시스턴트 작업',
        details: '상세'
      },
      columns: {
        time: '시간',
        action: '작업',
        target: '대상',
        actor: '시작자',
        outcome: '결과'
      }
    }
  },
  embedPublish: {
    copyCode: '코드 복사'
  },
  knowledgeList: {
    detail: {
      title: '공유 지식베이스',
      sourceOrg: '소스 스페이스',
      myPermission: '내 권한'
    },
    sections: {
      tenantOthers: '워크스페이스 · 다른 멤버',
      tenantReadonly: '워크스페이스 · 읽기 전용'
    },
    empty: {
      title: '지식베이스 없음'
    }
  },
  createChat: {
    title: '안녕하세요, Xiaozhi입니다 — 당신의 지식을 손끝에',
    newSessionTitle: '새 세션',
    openProject: '프로젝트 선택',
    clearProject: '바인딩 해제',
    pickFailed: '선택한 경로를 열 수 없습니다',
    messages: {
      createFailed: '세션 생성 실패',
      createError: '세션 생성 실패, 나중에 다시 시도해주세요'
    }
  },
  input: {
    addModel: '모델 추가',
    placeholder: '질문이나 작업 내용을 입력하세요…',
    agentMode: 'Agent 모드',
    normalMode: '일반 모드',
    normalModeDesc: '지식베이스 기반 RAG Q&A',
    agentModeDesc: 'ReAct 추론 프레임워크, 다단계 사고',
    agentMissingAllowedTools: '허용된 도구',
    agentMissingSummaryModel: '대화 모델',
    agentMissingRerankModel: '재정렬 모델',
    customAgentMissingSummaryModel: '대화 모델',
    customAgentMissingRerankModel: '재정렬 모델',
    goToAgentEditor: '구성으로 이동 →',
    agentNotReadyDetail: 'Agent "{agentName}"가 준비되지 않았습니다. 다음 항목을 설정해야 합니다: {reasons}',
    sharedAgentNotReadyDetail: '공유 Agent "{agentName}"가 준비되지 않았습니다(누락: {reasons}). 공유한 조직 관리자에게 구성을 요청하세요.',
    knowledgeBase: '지식베이스',
    knowledgeBaseWithCount: '지식베이스({count})',
    notConfigured: '구성되지 않음',
    sharedAgentModelLabel: '공유 에이전트에 구성된 모델',
    noModel: '사용 가능한 모델 없음',
    modelAuto: '기본',
    modelFollowDefault: '기본값 따르기',
    modelAutoHint: '현재 지식 베이스의 대화 모델을 사용하며, 지식 베이스 밖이거나 설정되지 않은 경우 첫 번째로 사용 가능한 대화 모델을 사용합니다',
    stopGeneration: '생성 중지',
    send: '전송',
    steerRetry: '다시 보내기',
    webSearchDisabledByAgent: '현재 에이전트에 대해서는 네트워크 검색이 비활성화되어 있습니다.',
    kbLockedByAgent: '현재 에이전트가 지식베이스 구성을 잠갔습니다.',
    kbDisabledByAgent: '현재 에이전트가 지식베이스 기능을 비활성화했습니다.',
    modelLockedByAgent: '현재 에이전트는 모델 구성을 잠갔습니다.',
    imageUploadDisabledByAgent: '현재 에이전트에서 이미지 업로드가 활성화되지 않았습니다',
    voiceTooltip: '길게 눌러 말하기 ({shortcut})',
    voicePreparing: '마이크를 준비하는 중입니다. 버튼이 빨간색이 되면 말하세요',
    voiceRecording: '녹음 중, 손을 떼면 종료됩니다',
    voiceReleasedEarly: '마이크가 아직 준비되지 않았습니다. 버튼이 빨간색이 될 때까지 누른 채 말하세요',
    voiceTranscribing: '음성을 인식하는 중…',
    voiceUnsupported: '현재 브라우저는 녹음을 지원하지 않습니다',
    voiceInsecureContext: '음성 입력은 HTTPS 또는 localhost에서만 사용할 수 있습니다',
    voicePermissionDenied: '마이크를 사용할 수 없습니다. 브라우저에서 마이크 권한을 허용하세요',
    voiceDeviceError: '사용 가능한 마이크가 없습니다',
    voiceDecodeError: '녹음 처리에 실패했습니다. 다시 시도하세요',
    voiceTranscribeFailed: '음성 인식에 실패했습니다. 에이전트의 ASR 모델 설정을 확인하세요',
    voiceEmptyResult: '인식된 음성이 없습니다',
    goToAgentSettings: '에이전트 설정으로 이동',
    hostApprovalMode: {
      ask: '승인 요청',
      askHint: '삭제와 작업 공간 밖 쓰기는 확인합니다',
      auto: '대신 승인',
      autoHint: '모델이 대신 판단하며 방해하지 않습니다',
      switchFailed: '승인 모드를 전환하지 못했습니다'
    },
    messages: {
      enterContent: '먼저 내용을 입력해주세요!',
      replying: '응답 중입니다. 잠시 후 다시 시도해주세요!',
      steerFailed: '메시지 추가에 실패했습니다. 다시 시도해주세요.',
      agentSwitchedOn: 'Agent 모드로 전환되었습니다',
      agentSwitchedOff: '일반 모드로 전환되었습니다',
      agentSelected: '"{name}" 에이전트가 선택되었습니다.',
      webSearchNotConfigured: '웹 검색 엔진이 구성되지 않았습니다. 먼저 설정에서 검색 엔진 선택 및 인터페이스 구성을 완료해주세요.',
      webSearchEnabled: '웹 검색이 켜졌습니다',
      webSearchDisabled: '웹 검색이 꺼졌습니다',
      sessionMissing: '세션 ID가 존재하지 않습니다',
      messageMissing: '메시지 ID를 가져올 수 없습니다. 페이지를 새로고침한 후 다시 시도해주세요',
      stopSuccess: '생성이 중지되었습니다',
      stopFailed: '중지 실패, 다시 시도해주세요'
    },
    webSearch: {
      toggleOn: '웹 검색 켜기',
      toggleOff: '웹 검색 끄기',
      notConfigured: '웹 검색 엔진이 구성되지 않았습니다'
    }
  },
  manualEditor: {
    defaultTitlePrefix: '새 문서',
    noDocumentKnowledgeBases: '사용 가능한 문서형 지식베이스가 없습니다. 먼저 문서형 지식베이스를 생성해주세요',
    actions: {
      cancel: '취소',
      saveDraft: '임시 저장',
      publish: '게시하기'
    },
    loading: {
      content: '내용 로딩 중',
      preparing: '편집기 준비 중'
    },
    status: {
      draftTag: '현재 상태: 임시 저장',
      publishedTag: '현재 상태: 게시됨',
      lastUpdated: '최근 업데이트: {time}',
      counter: '{chars}자 · {lines}줄'
    },
    form: {
      knowledgeBasePlaceholder: '지식베이스를 선택해주세요',
      titleLabel: '지식 제목',
      knowledgeBaseLabel: '대상 지식베이스',
      titlePlaceholder: '제목을 입력해주세요',
      contentPlaceholder: 'Markdown 구문을 지원합니다. # 제목, 목록, 코드 블록 등을 사용할 수 있습니다'
    },
    success: {
      draftSaved: '임시 저장됨',
      published: '지식이 게시되고 인덱싱이 시작되었습니다'
    },
    warning: {
      selectKnowledgeBase: '대상 지식베이스를 선택해주세요',
      enterTitle: '지식 제목을 입력해주세요',
      enterContent: '지식 내용을 입력해주세요',
      contentTooShort: '내용이 너무 짧습니다. 더 많은 정보를 추가한 후 게시하는 것을 권장합니다'
    },
    error: {
      fetchDetailFailed: '지식 세부 정보 가져오기 실패',
      saveFailed: '저장 실패, 나중에 다시 시도해주세요'
    },
    labels: {
      currentKnowledgeBase: '현재 지식베이스'
    },
    section: {
      content: '지식 내용'
    },
    title: {
      edit: 'Markdown 지식 편집',
      create: '온라인 Markdown 지식 편집'
    },
    preview: {
      empty: '내용 없음'
    },
    view: {
      edit: '편집',
      split: '분할',
      preview: '미리보기',
      splitUnavailable: '너비가 부족합니다. 서랍을 넓히거나 전체 화면으로 전환하세요',
      groupLabel: '편집기 보기'
    },
    shortcuts: {
      title: '단축키',
      continueList: '목록 이어쓰기',
      indent: '들여쓰기 / Shift+Tab 내어쓰기'
    },
    toolbar: {
      bold: '굵게',
      italic: '기울임',
      strike: '취소선',
      inlineCode: '인라인 코드',
      heading1: '제목 1',
      heading2: '제목 2',
      heading3: '제목 3',
      bulletList: '글머리 기호 목록',
      orderedList: '번호 목록',
      taskList: '작업 목록',
      blockquote: '인용',
      codeBlock: '코드 블록',
      link: '링크 삽입',
      image: '이미지 삽입',
      table: '표 삽입',
      horizontalRule: '구분선',
      headingGroup: '제목',
      insertGroup: '삽입'
    },
    table: {
      column1: '열1',
      column2: '열2',
      cell: '내용'
    },
    placeholders: {
      heading: '제목{level}',
      listItem: '목록 항목',
      taskItem: '작업 항목',
      quote: '인용 내용',
      code: '코드 내용',
      linkText: '링크 텍스트',
      imageAlt: '설명',
      bold: '굵은 텍스트',
      italic: '기울임 텍스트',
      strike: '취소선',
      inlineCode: 'code'
    },
    assistant: {
      button: '어시스턴트',
      tooltip: '어시스턴트에게 글쓰기 맡기기',
      continue: '이어 쓰기',
      outline: '개요 만들기',
      polish: '전체 다듬기',
      summarize: '요점 정리',
      open: '어시스턴트 열기',
      prompts: {
        continue: '본문 끝에서 앞 내용에 이어지는 문단을 하나 써 주세요.',
        outline: '제목과 현재 내용을 바탕으로 이 문서의 구조가 잘 드러나는 개요를 만들어 본문 맨 앞에 써 주세요.',
        polish: '본문을 다듬어 주세요. 오타와 어색한 문장을 고치되 의미는 바꾸지 말고 문단별로 고쳐 주세요.',
        summarize: '이 문서의 요점을 대화에서 정리해 주세요. 본문은 수정하지 마세요.'
      }
    }
  },
  file: {
    upload: '파일 업로드'
  },
  mentionDetail: {
    readOnlyFromAgent: '이 대화에서는 읽기 전용이며 지식베이스 목록에는 표시되지 않습니다.',
    faqCount: 'Q&A {count}개',
    kbCount: '문서 {count}개',
    mcpToolCount: '도구 {count}개',
    mcpNotSynced: '도구가 아직 동기화되지 않음',
    mcpStale: '다시 동기화 필요',
    belongsToKb: '지식베이스: ',
    belongsToOrg: '스페이스: ',
    noCompatibleKbForAgent: '현재 에이전트의 도구와 범위 내 지식베이스의 기능이 일치하지 않아 참조할 수 있는 지식베이스가 없습니다.',
    tag: '태그',
    searchPlaceholder: '지식베이스, 파일 등 검색',
    searchInGroup: '{group}에서 검색…',
    typeToSearch: '{\'@\'} 뒤에 계속 입력하여 검색…',
    viewAll: '모두 보기',
    back: '뒤로'
  },
  mentionBrowser: {
    browse: '폴더별 탐색',
    path: '폴더 경로',
    root: '루트',
    searchFolder: '이 폴더 검색',
    searchKb: '지식베이스 검색',
    subtree: '하위 폴더도 검색합니다.',
    wholeKb: '전체 지식베이스가 선택되어 있습니다. 파일을 선택해도 범위가 좁아지지 않습니다.',
    tags: '기존 태그가 선택한 파일을 계속 필터링합니다.',
    folderCount: '하위 폴더 포함 문서 {count}개',
    selected: '선택됨',
    deleting: '삭제 중',
    unsupported: '이 에이전트에서 지원하지 않는 형식',
    forbidden: '이 콘텐츠에 접근할 권한이 없습니다.',
    missing: '폴더가 더 이상 유효하지 않습니다. 돌아가서 다시 선택하세요.',
    error: '폴더를 불러오지 못했습니다. 다시 시도하세요.',
    retry: '다시 시도',
    empty: '이 보기에 파일이 없습니다.',
    previous: '이전',
    next: '다음',
    page: '{page}페이지 · 문서 {total}개'
  },
  common: {
    confirm: '확인',
    cancel: '취소',
    fullscreen: '전체 화면',
    exitFullscreen: '전체 화면 종료',
    save: '저장',
    delete: '삭제',
    edit: '편집',
    copy: '복사',
    copied: '복사됨',
    copySuccess: '복사되었습니다',
    loading: '로딩 중...',
    noMoreData: '모든 내용을 로드했습니다',
    loadMore: '더 보기',
    error: '오류',
    success: '성공',
    failed: '실패',
    selectAll: '전체 선택',
    yes: '예',
    no: '아니오',
    close: '닫기',
    back: '뒤로',
    next: '다음',
    finish: '완료',
    all: '전체',
    clear: '지우기',
    on: '켜기',
    off: '끄기',
    confirmDelete: '삭제 확인',
    deleteFailed: '삭제 실패',
    operationFailed: '작업 실패',
    file: '파일',
    skill: '스킬',
    knowledgeBase: '지식베이스',
    noResult: '결과 없음',
    remove: '제거',
    avatar: '아바타',
    defaultUser: '사용자',
    copyFailed: '복사 실패',
    retry: '재시도',
    expand: '펼치기',
    unsavedChanges: {
      title: '저장되지 않은 변경 사항',
      body: '지금 닫으면 변경 사항이 사라집니다. 닫으시겠습니까?',
      discard: '변경 사항 버리기',
      keepEditing: '계속 편집'
    }
  },
  authStore: {
    errors: {
      parseUserFailed: '사용자 정보 파싱 실패',
      parseTenantFailed: '워크스페이스 정보 파싱 실패',
      parseKnowledgeBasesFailed: '지식베이스 목록 파싱 실패',
      parseCurrentKnowledgeBaseFailed: '현재 지식베이스 파싱 실패'
    }
  },
  auth: {
    account: '계정',
    accountPlaceholder: '계정을 입력하세요',
    accountRequired: '계정을 입력해주세요',
    accountDescription: '플랫폼 로그인 계정',
    login: '로그인',
    logout: '로그아웃',
    oidcLogin: 'OIDC로 로그인',
    oidcLoginWithProvider: '{provider}(으)로 로그인',
    redirectingToOIDC: 'ID 공급자로 이동하는 중...',
    orContinueWith: '또는 다음 방법으로 계속',
    oidcLoginFailed: 'OIDC 로그인 실패',
    username: '사용자명',
    email: '이메일',
    password: '비밀번호',
    confirmPassword: '비밀번호 확인',
    loginSuccessTitle: '로그인 성공',
    loginSuccessContent: '환영합니다. {name} 에 입장했습니다',
    loggingIn: '로그인 중...',
    register: '회원가입',
    registering: '가입 중...',
    createAccount: '계정 생성',
    haveAccount: '이미 계정이 있으신가요?',
    backToLogin: '로그인으로 돌아가기',
    loginHint: '로그인하여 계속하세요. 처음이시라면 아래에서 계정을 만드세요.',
    firstTime: '처음 이용하시나요?',
    registerSuccess: '가입이 완료되었습니다. 로그인해주세요',
    registerFailed: '가입 실패',
    registerSubtitle: '계정을 만들고 시작하세요',
    emailPlaceholder: '이메일 주소 입력',
    passwordPlaceholder: '비밀번호 입력',
    confirmPasswordPlaceholder: '비밀번호 다시 입력',
    usernamePlaceholder: '사용자명 입력',
    emailRequired: '이메일 주소를 입력해주세요',
    emailInvalid: '올바른 이메일 형식을 입력해주세요',
    passwordRequired: '비밀번호를 입력해주세요',
    passwordMinLength: '비밀번호는 최소 8자여야 합니다',
    passwordMaxLength: '비밀번호는 1024자를 초과할 수 없습니다',
    passwordMustContainLetter: '비밀번호에 문자가 포함되어야 합니다',
    passwordMustContainLowercaseLetter: '비밀번호에는 소문자가 포함되어야 합니다',
    passwordMustContainUppercaseLetter: '비밀번호에는 대문자가 포함되어야 합니다',
    passwordMustContainNumber: '비밀번호에 숫자가 포함되어야 합니다',
    passwordMustContainSpecialChar: '비밀번호에는 특수문자가 포함되어야 합니다: {specialChars}',
    usernameRequired: '사용자명을 입력해주세요',
    usernameMinLength: '사용자명은 최소 2자여야 합니다',
    usernameMaxLength: '사용자명은 20자를 초과할 수 없습니다',
    usernameInvalid: '사용자명은 영문자, 숫자, 밑줄(_), 한자만 포함할 수 있습니다',
    confirmPasswordRequired: '비밀번호를 확인해주세요',
    passwordMismatch: '두 비밀번호가 일치하지 않습니다',
    loginError: '계정 또는 비밀번호를 확인하세요',
    loginErrorRetry: '로그인 오류, 나중에 다시 시도해주세요',
    registerError: '가입 오류, 나중에 다시 시도해주세요',
    workspaceOnboarding: {
      title: '작업 공간 선택',
      description: '계속하려면 개인 공간을 만드세요.',
      create: '공간 만들기',
      invitations: '초대 보기',
      loadingPolicy: '사용 가능한 공간 참여 방식을 확인하고 있습니다…',
      policyLoadFailed: '공간 권한을 불러올 수 없습니다. 네트워크를 확인한 후 다시 시도하세요.',
      retry: '다시 불러오기',
      inviteOnlyTitle: '작업 공간 초대 대기',
      inviteOnlyDescription: '개인 공간 만들기가 비활성화되어 있습니다. 관리자가 보낸 초대를 확인하고 수락하세요.',
      inviteOnlyNotice: '이 계정은 초대를 통해서만 기존 공간에 참여할 수 있습니다',
      help: '지금 작업 공간을 만들거나 나중에 돌아와 초대를 수락할 수 있습니다.',
      inviteOnlyHelp: '초대가 없다면 등록 이메일을 공간 관리자에게 전달하고 초대를 요청하세요.'
    }
  },
  inviteRegister: {
    bannerTitle: '「{tenant}」에 초대되었습니다',
    bannerHint: '아래 정보를 입력해 가입을 완료하세요. 등록이 끝나면 자동으로 팀에 합류합니다.',
    bannerHintLogin: '로그인하면 자동으로 팀에 합류됩니다.',
    loading: '초대 링크를 확인하는 중…',
    invalidTitle: '초대 링크가 유효하지 않거나 취소되었습니다',
    invalidBody: '초대한 분께 새 링크를 요청하거나 기존 계정으로 로그인하세요.',
    backToLogin: '로그인으로 돌아가기',
    title: '가입 완료',
    subtitle: '「{tenant}」에 초대되었습니다',
    email: '이메일',
    emailPlaceholder: 'your{\'@\'}example.com',
    emailHint: '본인이 사용하는 이메일이면 됩니다.',
    emailInvalid: '유효한 이메일을 입력해 주세요',
    username: '표시 이름',
    usernamePlaceholder: '이름을 입력하세요',
    password: '비밀번호 설정',
    passwordPlaceholder: '최소 6자 이상',
    confirmPassword: '비밀번호 확인',
    submit: '가입 완료',
    submitting: '전송 중…',
    success: '가입 완료, 워크스페이스로 이동합니다…',
    joined: '팀에 합류했습니다.',
    failed: '가입에 실패했습니다. 잠시 후 다시 시도해 주세요',
    usernameRequired: '이름을 입력하세요',
    passwordTooShort: '비밀번호는 최소 6자 이상이어야 합니다',
    passwordMismatch: '두 비밀번호가 일치하지 않습니다'
  },
  initialization: {
    skip: '건너뛰기',
    next: '다음'
  },
  graphSettings: {
    title: '지식 그래프 설정',
    description: '엔티티-관계 추출 기능을 구성하여 텍스트에서 자동으로 엔티티와 관계를 추출하여 지식 그래프를 구축합니다 (참고: Wiki의 \'페이지 링크 그래프\'와는 다릅니다. 후자는 Wiki 페이지 간의 참조 관계를 보여주며, 이쪽은 LLM이 추출한 엔티티-관계 그래프입니다)',
    enableLabel: '엔티티 관계 추출 활성화',
    enableDescription: '활성화하면 텍스트에서 자동으로 엔티티와 관계를 추출합니다',
    tagsLabel: '관계 유형',
    tagsDescription: '추출할 관계 유형 태그 정의, 여러 태그는 쉼표로 구분',
    tagsPlaceholder: '관계 유형 입력, 예: 근무처, 동료, 친구 등',
    generateRandomTags: '랜덤 태그 생성',
    sampleTextLabel: '샘플 텍스트',
    sampleTextDescription: '엔티티 관계 추출 테스트용 샘플 텍스트',
    sampleTextPlaceholder: '엔티티와 관계가 포함된 텍스트 입력...',
    customInstructionsLabel: '추가 추출 지침',
    customInstructionsDescription: '구조화된 출력 규칙은 유지하면서 도메인 범위와 엔티티 속성 지침을 추가합니다',
    customInstructionsPlaceholder: '예: 계약 당사자, 금액, 이행 기한 및 책임을 중점적으로 추출…',
    generateRandomText: '랜덤 텍스트 생성',
    entityListLabel: '엔티티 목록',
    entityListDescription: '텍스트에서 추출한 엔티티 및 속성',
    nodeNamePlaceholder: '엔티티 이름 입력',
    attributePlaceholder: '속성값 입력',
    addAttribute: '속성 추가',
    manageEntitiesLabel: '엔티티 관리',
    manageEntitiesDescription: '엔티티 노드 추가 또는 삭제',
    addEntity: '엔티티 추가',
    relationListLabel: '관계 목록',
    relationListDescription: '엔티티 간의 관계 연결 정의',
    selectEntity: '엔티티 선택',
    selectRelationType: '관계 유형 선택',
    manageRelationsLabel: '관계 관리',
    manageRelationsDescription: '엔티티 간 관계 추가 또는 삭제',
    addRelation: '관계 추가',
    extractActionsLabel: '추출 작업',
    extractActionsDescription: '엔티티 관계 추출 실행 또는 샘플 데이터 관리',
    startExtraction: '추출 시작',
    extracting: '추출 중...',
    defaultExample: '기본 예시',
    clearExample: '예시 지우기',
    completeModelConfig: '먼저 모델 설정을 완료하세요',
    tagsGenerated: '태그 생성 성공',
    tagsGenerateFailed: '태그 생성 실패',
    textGenerated: '텍스트 생성 성공',
    textGenerateFailed: '텍스트 생성 실패',
    pleaseInputText: '먼저 샘플 텍스트를 입력하세요',
    extractSuccess: '엔티티 관계 추출 성공',
    extractFailed: '엔티티 관계 추출 실패',
    exampleLoaded: '예시가 로드되었습니다',
    exampleCleared: '예시가 지워졌습니다',
    checkingAvailability: '지식 그래프 사용 가능 여부를 확인하는 중…',
    checkAvailabilityFailed: '지식 그래프 사용 가능 여부를 확인할 수 없습니다. 다시 시도해 주세요.',
    disabledWarning: '지식 그래프 데이터베이스가 활성화되지 않아 엔티티 관계 추출 기능을 사용할 수 없습니다',
    howToEnable: '지식 그래프를 활성화하는 방법?'
  },
  retrievalSettings: {
    title: '검색 설정',
    description: '지식베이스 검색과 메시지 검색이 공유하는 전역 검색 파라미터를 설정합니다. 값은 ContextDB 공식 검색 API에 그대로 전달됩니다',
    topKLabel: '검색 반환 수 (Top K)',
    topKDescription: '한 번의 검색이 반환하는 청크 수, 범위 1–10. ContextDB 공식 기본값은 5',
    similarityThresholdLabel: '유사도 임계값',
    similarityThresholdDescription: '이 관련성보다 낮은 청크는 필터링됩니다. 범위 0–1. ContextDB 공식 기본값은 0.6',
    vectorWeightLabel: '벡터 가중치',
    vectorWeightDescription: '벡터 검색과 키워드 검색의 균형 가중치. 범위 0–1. ContextDB 공식 기본값은 0.7',
    queryRewriteLabel: '쿼리 재작성',
    queryRewriteDescription: '검색 전 ContextDB가 LLM으로 쿼리를 재작성해 재현율을 높입니다. 공식 기본값은 꺼짐, 플랫폼 기본값은 켜짐',
    toasts: {
      saveSuccess: '검색 설정이 저장되었습니다',
      saveFailed: '설정 저장 실패: {message}'
    }
  },
  defaultSettings: {
    saving: '저장 중',
    loadFailed: '기본 설정을 불러오지 못했습니다. 편집하기 전에 다시 시도하세요.',
    title: '기본 설정',
    readOnly: '워크스페이스 관리자만 변경할 수 있습니다. 현재 적용 중인 기본값은 확인할 수 있습니다.',
    webSearchGroup: '웹 검색',
    toasts: {
      saveFailed: '저장 실패: {message}'
    },
    webSearch: {
      label: '기본 검색 엔진',
      description: '자체 검색 엔진이 없는 에이전트에서 웹 검색을 켜면 사용합니다.',
      unset: '기본 검색 엔진이 없습니다. 자체 검색 엔진이 없는 에이전트는 웹 검색을 할 수 없습니다.',
      placeholder: '검색 엔진 선택'
    },
    hints: {
      workspace: '워크스페이스 설정을 사용 중입니다.',
      system: '설정 안 됨. 현재 시스템 기본값 사용 중: {name}',
      auto: '설정 안 됨. 현재 첫 번째 사용 가능 모델 사용 중: {name}',
      followChat: '설정 안 됨. 기본 대화 모델을 따릅니다: {name}',
      staleFallback: '선택한 모델이 삭제되었거나 사용할 수 없습니다. 현재 대체 모델: {name}',
      staleNone: '선택한 모델이 삭제되었거나 사용할 수 없으며, 대체할 모델도 없습니다.'
    },
    slots: {
      asr: {
        label: '기본 음성 인식 모델',
        description: '오디오·비디오 전사의 기본 선택입니다.',
        none: '사용 가능한 음성 인식 모델이 없어 전사를 사용할 수 없습니다.'
      },
      vlm: {
        label: '기본 비전 모델',
        description: '이미지 이해와 멀티모달 파싱의 기본 선택입니다.',
        none: '사용 가능한 비전 모델이 없어 이미지 이해를 사용할 수 없습니다.'
      },
      rerank: {
        label: '기본 Rerank 모델',
        description: '자체 재정렬 모델이 없는 검색과 내장 에이전트에서 사용합니다.',
        none: '사용 가능한 Rerank 모델이 없어 검색 결과가 검색 순서대로 반환됩니다.'
      },
      embedding: {
        label: '기본 Embedding 모델',
        description: '새 지식베이스를 만들 때 기본으로 선택됩니다. 기존 지식베이스에는 영향이 없습니다.',
        none: '사용 가능한 Embedding 모델이 없어 지식베이스를 만들 수 없습니다.'
      },
      utility: {
        label: '경량 생성 모델',
        description: '세션 제목, MCP 사용 안내 같은 짧은 텍스트 작업에 사용합니다. 더 빠르고 저렴한 모델을 권장합니다.',
        none: '사용 가능한 대화 모델이 없어 제목과 안내를 생성할 수 없습니다.'
      },
      chat: {
        label: '기본 대화 모델',
        description: '새 에이전트와 Q&A에서 사용하며, 백그라운드 작업의 대체 모델로도 쓰입니다.',
        none: '사용 가능한 대화 모델이 없어 Q&A와 백그라운드 생성을 사용할 수 없습니다.'
      }
    }
  },
  envVarSettings: {
    host: {
      title: '환경 변수'
    }
  },
  settings: {
    modelManagement: '모델 관리',
    autoCheckUpdate: '업데이트 자동 다운로드',
    autoCheckUpdateDesc: '활성화하면 시작 시 최신 버전을 자동으로 확인하고 백그라운드에서 다운로드합니다.',
    parserEngine: '파싱 엔진',
    mcpService: 'MCP 서비스',
    workspaceSettings: '워크스페이스 설정',
    capabilityUnavailable: '현재 배포에서는 이 기능을 지원하지 않습니다. 사용 가능한 페이지로 돌아갔습니다.',
    hostApprovalDefault: {
      title: '기본 실행 권한 승인',
      description: '에이전트가 파일을 삭제하거나 작업 영역 밖에 쓸 때, 매번 물어볼지 모델이 대신 승인할지를 정합니다. 새 대화는 여기서 시작하고, 현재 대화는 입력창 왼쪽에서 바꿀 수 있습니다.'
    },
    storage: {
      title: '스토리지 엔진',
      engineLocal: 'Local（로컬）',
      engineCos: 'Tencent Cloud COS',
      engineTos: 'Volcengine TOS',
      engineOss: 'Alibaba Cloud OSS'
    },
    parser: {
      title: '파서 엔진'
    },
    roleDenied: {
      title: '권한 없음',
      desc: '현재 역할로는 이 설정 페이지에 접근할 수 없습니다. 이 워크스페이스의 관리자에게 필요한 역할을 요청하세요.'
    },
    navGroups: {
      systemAdministration: '시스템 관리'
    },
    skills: {
      nativeUsage: 'Select packages in the agent configuration. Scripts require OpenSandbox and suitable dependencies; a catalog entry does not prove dependencies are installed.',
      addSourceDescription: 'Import a directory containing one SKILL.md, references and scripts. Importing records content and does not execute an installer.',
      title: '스킬 관리',
      description: 'Manage skill packages. Selected instructions and references are loaded by SkillsMiddleware; uploading does not install dependencies.',
      helpTooltip: 'The catalog holds instructions, references and scripts. Scripts run in the session sandbox; dependencies come from its deployed image.',
      addSkill: '스킬 추가',
      addStepRegister: '등록',
      addFileSelected: '{name} 선택됨',
      addClearFile: '지우기',
      emptyDesc: 'No skill packages yet. Upload a ZIP or add a source.',
      deleteCatalog: '카탈로그에서 삭제',
      deleteCatalogConfirm: 'Delete “{name}” from the catalog? Historical installation records remain; referenced entries cannot be deleted.',
      deleteSuccess: '카탈로그에서 삭제했습니다',
      registerAccepted: '카탈로그에 추가했습니다',
      loadFailed: '불러오지 못했습니다'
    },
    sandbox: {
      title: '샌드박스 설정',
      skillUploadClick: 'zip 파일을 클릭해 업로드',
      skillUploadDrag: '또는 여기로 드래그',
      skillSourceSection: '소스에서 설치',
      skillSourceSectionHint: 'ClawHub, GitHub 또는 SkillHub 링크, 혹은 {\'@\'}owner/slug를 붙여넣으세요. 압축 파일은 {size} MB를 넘을 수 없습니다.',
      skillUploadSection: '로컬 번들 업로드',
      skillUploadSectionHint: 'SKILL.md가 포함된 zip을 아래로 끌어다 놓거나 클릭해서 선택하세요. 압축 파일은 {size} MB를 넘을 수 없습니다.',
      skillSourcePlaceholder: 'ClawHub는 {\'@\'}owner/slug, GitHub/SkillHub는 전체 URL을 붙여넣으세요',
      skillSourceFailed: '레지스트리에서 스킬을 설치하지 못했습니다',
      skillUploadFailed: 'Failed to upload the skill',
      skillBundleTooLarge: '스킬 압축 파일은 {size} MB를 넘을 수 없습니다.',
      skillBundleTooManyFiles: '스킬 디렉터리의 파일은 {count}개를 넘을 수 없습니다.',
      skillBundleTooManyZipEntries: '압축 파일 항목은 {count}개를 넘을 수 없습니다.',
      installCommandRunning: '명령 실행 중',
      skillFiles: '파일 보기',
      skillFilesTitle: '파일',
      skillFilesEmpty: '이 스킬에서 볼 수 있는 파일이 아직 없습니다.',
      skillFilesLoadFailed: '스킬 파일을 불러오지 못했습니다',
      skillFilesFileLoadFailed: '이 파일을 읽을 수 없습니다',
      skillFilesBinary: '이 파일은 바이너리라 미리볼 수 없습니다.',
      skillFilesTruncated: '파일이 커서 앞부분만 표시합니다.',
      skillFilesSelectHint: '왼쪽에서 파일을 선택하면 내용을 볼 수 있습니다',
      skillFilesPreview: '미리보기',
      skillFilesSource: '원본',
      skillDisabled: 'Skill disabled',
      installCommandWaiting: '명령 출력을 기다리는 중입니다. 경과 시간은 계속 업데이트됩니다.'
    }
  },
  agent: {
    taskLabel: '작업:',
    think: '사고',
    copy: '복사',
    addToKnowledgeBase: '지식베이스에 추가',
    updatePlan: '계획 업데이트',
    webSearchFound: '<strong>{count}</strong>개의 웹 검색 결과 발견',
    toolFallback: '도구',
    stepsCompleted: '<strong>{steps}</strong>개 단계 완료',
    reasoningRounds: '사고 <strong>{rounds}</strong>회',
    earlierSteps: '이전 단계 {count}개',
    viewReasoning: '사고 과정 보기',
    toolCalls: '도구 <strong>{tools}</strong>회 호출',
    durationSuffix: '소요 시간 <strong>{duration}</strong>',
    stepSummarySeparator: ' · ',
    contextCompacted: '컨텍스트 압축',
    contextCompactedSummary: '{before} → {after} 토큰',
    contextCompactedDegraded: '요약을 사용할 수 없어 원본 기록을 유지했습니다',
    title: '에이전트',
    subtitle: '에이전트 구성 및 관리, 대화 동작 및 기능 맞춤화',
    createAgent: '에이전트 만들기',
    builtin: '내장',
    disabled: '비활성화됨',
    disable: '비활성화',
    enable: '활성화',
    noDescription: '아직 설명이 없습니다',
    selectAgent: '에이전트 선택',
    noAgents: '아직 에이전트가 없습니다.',
    manageAgents: '관리',
    builtinAgents: '내장된 인텔리전스',
    customAgents: '맞춤형 에이전트',
    selector: {
      title: '에이전트 선택',
      current: '현재 선택',
      goToSettings: '설정',
      sharedLabel: '공유',
      notReadyHint: '아직 구성 필요: {items}',
      notReadyStatus: '구성 필요',
      configureAction: '구성',
      sharedNotReadyContact: '공유한 조직 관리자에게 구성을 요청하세요',
      capabilitiesSection: '능력',
      webSearchCapability: '웹 검색',
      imageUploadCapability: '이미지 업로드',
      capabilityEnabled: '켜짐',
      capabilityDisabled: '꺼짐',
      capabilitySupported: '지원',
      capabilityUnsupported: '미지원',
      capabilityUnconfigured: '미구성'
    },
    editor: {
      assistantChanged: '어시스턴트가 이 에이전트를 변경했습니다. 최신 설정을 보려면 다시 여세요.',
      assistantDeleted: '어시스턴트가 이 에이전트를 삭제했습니다.',
      reasoningEffortUnsupported: '선택한 모델은 사고를 지원하지 않습니다. "끄기" 외의 옵션은 무시됩니다.',
      reasoningEffortAlwaysOn: '선택한 모델은 항상 사고하며 끌 수 없습니다. 강도만 조정할 수 있습니다.',
      createTitle: '에이전트 만들기',
      editTitle: '에이전트 편집',
      basicInfo: '기본정보',
      basicInfoDesc: '에이전트 이름, 설명 및 실행 모드 구성',
      promptsConfig: '프롬프트',
      promptsConfigDesc: '시스템/컨텍스트/의도/재작성/폴백 프롬프트 구성',
      modelConfig: '모델 구성',
      modelConfigDesc: '대화 모델, ReRank 등 보조 모델 및 생성 매개변수 구성',
      toolsConfig: '도구 구성',
      toolsConfigDesc: '에이전트가 사용할 수 있는 도구 구성',
      knowledgeConfig: '지식베이스',
      knowledgeConfigDesc: '에이전트가 액세스할 수 있는 지식베이스 범위 및 FAQ 전략 구성',
      agentId: '에이전트 ID',
      agentIdDesc: 'API 연동에서 이 ID로 에이전트를 지정할 수 있습니다',
      name: '이름',
      namePlaceholder: '에이전트 이름을 입력해주세요.',
      nameRequired: '에이전트 이름을 입력해주세요.',
      systemPromptRequired: '시스템 프롬프트를 입력하세요.',
      modelRequired: '모델을 선택하세요.',
      queryMissingInRewrite: '재작성 사용자 프롬프트에는 {\'{{\'}query{\'}}\'} 플레이스홀더가 포함되어야 합니다.',
      queryMissingInFallback: '폴백 프롬프트에는 {\'{{\'}query{\'}}\'} 플레이스홀더가 포함되어야 합니다.',
      description: '설명',
      descriptionPlaceholder: '에이전트 설명을 입력하세요.',
      normalDesc: '신속하게 응답하고 질문에 직접 답변하세요.',
      agentDesc: '복잡한 문제에 대한 다단계 사고와 심층 분석',
      model: '모델',
      modelPlaceholder: '모델을 선택하세요.',
      systemPrompt: '시스템 프롬프트',
      systemPromptPlaceholder: '에이전트의 동작과 역할을 정의하는 사용자 지정 시스템 프롬프트(웹 검색 동작을 동적으로 제어하려면 {\'{{\'}web_search_status{\'}}\'} 플레이스홀더 사용)',
      contextTemplateRequired: '컨텍스트 템플릿을 입력하십시오.',
      temperature: '온도',
      thinking: '사고 모델',
      citationEnabled: '출처 인용 표시',
      citationEnabledDesc: '최종 답변에 지식베이스와 웹 출처를 표시합니다. 꺼도 검색과 근거 활용은 계속 작동합니다.',
      mode: '작동 모드',
      knowledgeBases: '관련 지식베이스',
      allKnowledgeBases: '모든 지식베이스',
      selectedKnowledgeBases: '지식베이스 지정',
      noKnowledgeBase: '지식베이스를 사용하지 않음',
      selectKnowledgeBases: '지식베이스 선택',
      selectKnowledgeBasesDesc: '연결할 지식베이스 선택(협업 지식베이스 포함)',
      myKnowledgeBases: '내 지식베이스',
      sharedKnowledgeBases: '협업 지식베이스',
      retrieveKBOnlyWhenMentioned: '언급된 경우에만 검색',
      retrieveKBOnlyWhenMentionedDesc: '꺼짐: 구성된 지식베이스를 자동으로 검색합니다. 켜짐: 사용자 {\'@\'}이 언급한 경우에만 검색합니다.',
      rerankModel: '리랭크 모델',
      rerankModelDesc: '지식베이스 검색 결과를 재정렬하여 답변 정확도를 높입니다',
      rerankModelPlaceholder: 'ReRank 모델을 선택하세요.',
      rerankModelOptionalHint: '현재 범위에 RAG 유형의 지식베이스가 없으므로 선택 사항입니다. 이후 RAG 지식베이스가 추가되면 워크스페이스 기본 ReRank 모델로 자동 폴백되지만, 명시적으로 설정하는 것을 권장합니다.',
      maxIterations: '주 에이전트 모델 호출 한도',
      maxIterationsLimit: '제한',
      maxIterationsUnlimited: '제한 없음',
      allowedTools: '허용된 도구',
      retrievalStrategy: '검색 전략',
      contextTemplate: '컨텍스트 템플릿',
      contextTemplatePlaceholder: '사용자 정의 컨텍스트 템플릿..',
      queryUnderstandModel: '질문 이해 모델',
      queryUnderstandModelPlaceholder: '비워 두면 기본 대화 모델을 사용합니다',
      rewritePromptSystem: '시스템 프롬프트 다시 작성',
      rewritePromptSystemPlaceholder: '시스템 기본 프롬프트를 사용하려면 비워 두세요.',
      rewritePromptUser: '사용자 프롬프트 다시 작성',
      rewritePromptUserPlaceholder: '시스템 기본 프롬프트를 사용하려면 비워 두세요.',
      maxCompletionTokens: '생성된 토큰의 최대 수',
      maxCompletionTokensDefault: '기본값',
      maxCompletionTokensCustom: '사용자 지정',
      fallbackStrategy: '폴백 전략',
      fallbackResponse: '고정 응답 내용',
      fallbackResponsePlaceholder: '죄송합니다. 이 질문에는 답변해 드릴 수 없습니다.',
      fallbackPrompt: '폴백 프롬프트',
      fallbackPromptPlaceholder: '시스템 기본 프롬프트를 사용하려면 비워 두세요.',
      skillsConfig: '스킬',
      skillsSelection: '스킬 목록',
      skillsAll: '전체',
      skillsSelected: '지정',
      skillsNone: '비활성화',
      skillsGroupUnavailable: '사용 불가',
      noSkillsAvailable: '워크스페이스 카탈로그에 스킬이 없습니다.',
      goSandboxSettings: '샌드박스 관리',
      sandboxBackend: '실행 샌드박스',
      memoryEnabled: '장기 기억',
      nativeRuntime: {
        adoptRuntime: '현재 실행 설정 적용',
        incompatible: '현재 배포의 실행 정책과 호환되지 않는 값이 있습니다. 아래 변경을 확인하세요. 적용하면 초안만 변경되며 저장 후 반영됩니다.',
        adoptQuick: '현재 네이티브 빠른 답변 설정 적용',
        changesPending: '변경 사항이 초안에 적용되었습니다. 저장 후 반영됩니다.',
        removed: '필드 제거',
        defaultsUnavailable: '현재 실행 기본값을 불러오지 못했습니다. 저장하기 전에 다시 불러오세요.',
        retry: '다시 불러오기',
        resolveBeforeSave: '호환되지 않는 설정을 해결한 후 저장하세요.',
        quickDesc: '빠른 답변은 네이티브 에이전트로 필요에 따라 검색하고 답변하며 별도의 모델 호출 한도를 사용합니다.',
        promptDesc: '현재 모드의 시스템 지침 또는 템플릿 참조를 설정합니다'
      },
      postCreateHint: {
        title: '생성 완료',
        footer: '설정을 계속 조정하고 공유·배포 채널을 구성한 뒤 "저장 후 닫기"를 클릭하세요.'
      },
      buttons: {
        create: '에이전트 만들기',
        saveAndClose: '저장 후 닫기'
      }
    },
    messages: {
      created: '에이전트가 성공적으로 생성되었습니다.',
      updated: '에이전트가 업데이트되었습니다.',
      deleted: '에이전트가 삭제되었습니다.',
      deleteFailed: '삭제 실패',
      saveFailed: '저장 실패',
      copied: '에이전트가 복사되었습니다.',
      copyFailed: '복사 실패',
      disabled: '비활성화됨',
      enabled: '활성화됨'
    },
    delete: {
      confirmTitle: '에이전트 삭제',
      confirmMessage: '"{name}" 에이전트를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.'
    },
    shareScope: {
      title: '공유 범위 설명',
      desc: '스페이스 구성원은 읽기 전용 모드로 에이전트를 사용하며 현재 구성된 기능과 리소스를 따릅니다. 에이전트에 대한 수정 사항은 공유 공간에 동기화됩니다. 스페이스 구성원이 지식베이스 콘텐츠를 편집할 수 있도록 허용하려면 지식베이스를 스페이스에 공유하세요.',
      knowledgeBase: '지식베이스',
      chatModel: '대화 모델',
      rerankModel: '모델을 재배열하다',
      webSearch: '웹 검색',
      mcp: 'MCP 서비스',
      kbAll: '모든 지식베이스',
      kbSelected: '{count} 지식베이스 지정',
      kbNone: '사용되지 않음',
      modelConfigured: '구성된',
      modelNotSet: '구성되지 않음',
      enabled: '켜다',
      disabled: '비활성화',
      mcpAll: '모든 서비스',
      mcpSelected: '{count} 서비스 지정',
      mcpNone: '사용되지 않음'
    },
    detail: {
      title: '에이전트 세부정보',
      useInChat: '대화에 사용'
    },
    empty: {
      title: '아직 맞춤 에이전트가 없습니다.',
      description: '첫 번째 에이전트를 생성하려면 오른쪽 상단에 있는 버튼을 클릭하세요.',
      sharedTitle: '아직 공유 에이전트가 없습니다.',
      sharedDescription: '스페이스에 참여하거나 다른 사람에게 에이전트를 공유하도록 요청할 수 있습니다.',
      favoritesTitle: '즐겨찾기 없음',
      favoritesDescription: '카드의 별표 아이콘을 눌러 즐겨찾기에 추가하세요',
      recentsTitle: '최근 항목 없음',
      recentsDescription: '최근에 사용한 에이전트가 여기에 표시됩니다'
    },
    sections: {
      builtin: '내장',
      mine: '내가 만듦',
      tenantOthers: '워크스페이스 · 다른 멤버',
      tenantReadonly: '워크스페이스 · 읽기 전용',
      sharedByMe: '내가 공유한',
      sharedEditable: '공유받음 · 편집 가능',
      sharedReadonly: '공유받음 · 읽기 전용'
    },
    tabs: {
      sharedToMe: '나와 공유됨'
    },
    features: {
      webSearch: '웹 검색 지원',
      knowledgeBase: '관련 지식베이스',
      mcp: 'MCP 서비스 지원',
      multiTurn: '여러 라운드의 대화'
    },
    mode: {
      normal: '빠른 Q&A',
      agent: '에이전트 추론'
    },
    type: {
      normal: '빠른 Q&A',
      agent: '에이전트 추론'
    },
    capabilities: {
      kbCount: '{count} 지식베이스 지정',
      kbAll: '전체 지식베이스에 액세스',
      mcpEnabled: 'MCP 서비스 활성화',
      multiTurn: '여러 라운드의 대화'
    },
    artifactDrawer: {
      buttonTitle: '이 응답에서 생성된 파일 보기',
      title: '생성된 파일',
      empty: '이번 회차에서 다운로드 가능한 파일이 없습니다.',
      preview: '미리보기',
      previewBack: '목록으로',
      collecting: '생성된 파일을 저장하는 중…',
      delete: '삭제',
      deleteTitle: '이 파일을 삭제할까요?',
      deleteConfirm: '「{name}」과(와) 저장된 내용이 영구적으로 삭제되며 복구할 수 없습니다.',
      deleted: '파일을 삭제했습니다',
      deleteFailed: '삭제에 실패했습니다. 다시 시도해 주세요.',
      download: '다운로드',
      downloadFailed: '다운로드에 실패했습니다. 다시 시도해 주세요.',
      inlinePreviewHint: '클릭하여 미리보기',
      inlineMissing: '파일을 사용할 수 없습니다',
      inlineDeleted: '삭제된 파일'
    }
  },
  knowledgeStages: {
    expandBranch: '하위 항목 펼치기',
    collapseBranch: '하위 항목 접기',
    resizeDrawer: '패널 너비 조절',
    status: {
      pending: '대기 중',
      running: '진행 중',
      finalizing: '최적화 중',
      done: '완료',
      failed: '실패',
      skipped: '건너뜀',
      cancelled: '취소됨'
    },
    stage: {
      docreader: '문서 파싱',
      chunking: '청킹',
      embedding: '벡터화',
      multimodal: '멀티모달 인식',
      postprocess: '후처리'
    },
    stall: {
      title: '{minutes}분 동안 진행이 없어 멈췄을 수 있습니다'
    },
    processConfig: {
      title: '이번 파싱 설정'
    }
  },
  uploadConfirm: {
    imageEmbeddingModel: '이미지 인덱싱 Embedding 모델',
    imageIndexInherited: '이미지 인덱싱에는 지식 베이스에 연결된 Embedding 모델을 사용합니다. 변경하려면 지식 베이스 설정으로 이동하세요.',
    imageVectorIndex: '이번 가져오기의 이미지 벡터 인덱싱',
    imageVectorIndexHint: '이번 업로드 또는 재분석에서 이미지 벡터를 생성하며 지식 베이스 기본 설정은 변경하지 않습니다. 검색 사용 여부는 지식 베이스의 이미지 벡터 검색 설정을 따릅니다.',
    imageVectorRequiresIndex: '먼저 지식 베이스 설정에서 벡터 인덱싱을 활성화하세요.',
    documentSummary: '문서 요약',
    documentSummaryDescription: '이번에 가져오는 문서의 요약을 자동으로 생성할지 선택합니다.',
    generateSummary: '문서 요약 생성',
    generateSummaryHint: '기본적으로 활성화됩니다. 비활성화하면 요약 생성을 건너뛰며 파싱, 인덱싱 및 기타 단계는 설정대로 진행됩니다.',
    title: '문서 업로드 확인',
    parseConfig: '파싱 설정',
    configNav: '파싱 설정 탐색',
    navParserDefault: '기본',
    navParserCustomized: '사용자 지정',
    moreOptions: '추가 처리 옵션',
    summaryParentChildShort: '부모-자식 청킹',
    summaryParserForceScanned: '스캔 문서 파싱',
    summaryQuestionCountValue: '{count}개',
    summaryGraphTagsValue: '{count}개',
    navChunkingSummary: '청크 {size}',
    statusOn: '켜짐',
    statusOff: '꺼짐',
    notSet: '미설정',
    summaryNoTags: '미설정',
    summaryTagsCount: '태그 {count}개',
    confirm: '업로드 및 파싱 확인',
    cancel: '취소',
    tabTags: '문서 태그',
    tagsDescription: '이 배치로 가져오는 모든 문서에 적용할 태그를 여러 개 선택할 수 있습니다',
    tagsPlaceholder: '태그 선택(복수 선택 가능)',
    tagsEmpty: '현재 지식 베이스에 태그가 없습니다. 업로드 후 태그 관리에서 만들 수 있습니다.',
    tagsLoadFailed: '태그를 불러오지 못했습니다. 나중에 문서 목록에서 설정할 수 있습니다.',
    noItems: '파일 또는 URL을 하나 이상 추가하세요',
    urlItemLabel: 'URL',
    urlAdded: 'URL이 추가되었습니다',
    urlDuplicate: '이 URL은 이미 목록에 있습니다',
    statusNeedsSetup: '설정 필요',
    multimodalSetupHint: '이미지가 포함되어 있습니다. 멀티모달을 활성화하고 모델을 선택하세요',
    asrSetupHint: '오디오가 포함되어 있습니다. 음성 인식을 활성화하고 모델을 선택하세요',
    vlmModelRequired: '멀티모달 모델을 설정하세요',
    asrModelRequired: '음성 인식 모델을 설정하세요',
    vlmModelSelectRequired: '멀티모달이 활성화되었습니다. VLM 모델을 선택하세요',
    asrModelSelectRequired: '음성 인식이 활성화되었습니다. ASR 모델을 선택하세요',
    continueAdd: '계속 추가',
    destinationLabel: '업로드 위치',
    destinationChange: '업로드 위치 변경',
    filesAdded: '{count}개 파일이 추가되었습니다',
    filesAllDuplicate: '선택한 파일이 이미 목록에 있습니다',
    titleManual: '온라인 편집 게시 확인',
    confirmManual: '게시 및 파싱',
    titleReparse: '재파싱 확인',
    confirmReparse: '확인 후 재파싱',
    reparseSource: '재파싱할 문서',
    reparseHint: '이전 파싱 설정을 사용하며 여기서 조정할 수 있습니다',
    manualCharCount: '{count}자',
    pdfForceScanned: {
      label: '스캔 PDF로 파싱',
      description: '웹 인쇄, 스캔본, 이미지 위주 PDF에 적합합니다. 모든 페이지를 이미지로 렌더링한 뒤 OCR/VLM으로 처리합니다. 처리 시간과 모델 호출 비용이 늘어날 수 있습니다.'
    }
  },
  knowledgeBase: {
    videosFilteredNoVLM: '{count}개의 동영상 파일을 건너됨 (동영상 업로드 미지원)',
    importURL: '웹페이지 가져오기',
    addDocument: '문서 추가',
    importURLTitle: '웹페이지 가져오기',
    urlRequired: 'URL을 입력하세요',
    invalidURL: '유효한 URL을 입력하세요',
    urlLabel: 'URL 주소',
    urlPlaceholder: '웹페이지 URL을 입력하세요. 예: https://example.com',
    urlTip: '다양한 웹페이지 콘텐츠를 가져올 수 있으며, 시스템이 자동으로 텍스트를 추출하고 분석합니다',
    channelLabel: '출처 채널',
    channelWeb: '웹',
    channelApi: 'API',
    channelBrowserExtension: '브라우저 확장',
    channelWechat: 'WeChat',
    channelWecom: 'WeCom',
    channelFeishu: 'Feishu',
    channelDingtalk: 'DingTalk',
    channelSlack: 'Slack',
    channelIm: 'IM 채널',
    channelConfluence: 'Confluence',
    channelGitLab: 'GitLab',
    channelNextcloud: 'Nextcloud',
    channelSeafile: 'Seafile',
    channelIma: 'Tencent IMA',
    channelUnknown: '알 수 없음',
    selectedCount: '{count}개 선택됨',
    pdfDocFormat: 'pdf, doc 형식 파일, 최대 {size}MB',
    textMarkdownFormat: 'text, markdown 형식 파일, 최대 {size}MB',
    dragFileNotText: '텍스트나 링크가 아닌 파일을 드래그하세요',
    searchPlaceholder: '지식베이스 검색...',
    noMatch: '일치하는 지식베이스를 찾을 수 없음',
    noKnowledge: '사용 가능한 지식베이스 없음',
    loadingFailed: '지식베이스 로드 실패',
    allFilesSkippedNoEngine: '선택한 모든 파일이 사용 가능한 파싱 엔진이 없어 건너뛰었습니다',
    filesSkippedNoEngine: '{count}개 파일이 사용 가능한 파싱 엔진이 없어 건너뛰었습니다',
    moveToFolder: {
      action: '폴더로 이동',
      newFolderPlaceholder: '새 폴더 이름',
      newFolderAddRoot: '루트 아래에 하위 디렉터리 만들기',
      newFolderAddUnder: '「{folder}」 아래에 하위 디렉터리 만들기',
      duplicate: '이미 존재하는 폴더입니다'
    },
    folderTree: {
      title: '폴더',
      rootRow: '루트'
    },
    sort: {
      title: '정렬'
    },
    infoCard: {
      title: '지식베이스 정보'
    }
  },
  resourceOrigin: {
    mine: '내 생성',
    mineTooltip: '현재 사용자가 생성',
    tenant: '워크스페이스',
    tenantTooltip: '워크스페이스의 다른 멤버가 생성',
    tenantTooltipWithCreator: '{creator}님이 생성',
    space: '스페이스',
    spaceTooltip: '공유 공간 「{space}」에서 가져옴',
    spaceTooltipWithTenant: '공유 공간 「{space}」 · 출처 {tenant}',
    shared: '외부 공유',
    sharedTooltip: '공유 공간를 통해 외부 워크스페이스에서 접근'
  },
  listSpaceSidebar: {
    all: '모두',
    workspace: '워크스페이스',
    spaces: '나와 공유됨',
    favorites: '즐겨찾기',
    recents: '최근'
  },
  batchManage: {
    selectAll: '전체 선택',
    cancel: '취소',
    delete: '대화 삭제',
    deleteConfirmTitle: '대화 삭제',
    deleteConfirmBody: '선택한 {count}개의 대화를 삭제하시겠습니까? 삭제 후 복구할 수 없습니다.',
    deleteAllConfirmBody: '모든 대화를 삭제하시겠습니까? 이 작업은 취소할 수 없습니다.',
    deleteSuccess: '삭제 성공',
    deleteFailed: '삭제 실패, 나중에 다시 시도해 주세요'
  },
  contextualGuide: {
    stepOf: '{current} / {total}',
    skip: '건너뛰기',
    prev: '이전',
    next: '다음',
    done: '확인',
    interactHint: '강조된 영역을 클릭하여 계속하세요',
    chat: {
      steps: {
        done: {
          title: '이제 탐색해 보세요',
          desc: '업로드한 문서와 관련된 질문을 해 보고, 인용이 포함된 답변을 확인해 보세요.'
        },
        send: {
          title: '보내기로 대화 시작',
          desc: '전송하면 새 세션이 만들어지고, AI가 지식 베이스를 바탕으로 인용과 함께 답변합니다.'
        },
        input: {
          title: '질문 입력',
          desc: '알고 싶은 내용을 입력하거나, 위의 추천 질문을 눌러 빠르게 시작하세요.'
        },
        kb: {
          title: '지식 범위 선택',
          desc: '{\'@\'}를 눌러 지식 베이스나 파일을 선택하세요. 선택한 범위만 사용해 답변합니다. 선택하지 않으면 현재 에이전트 설정이 적용됩니다.'
        }
      }
    },
    kbDetail: {
      steps: {
        done: {
          title: '분석 후 사용 가능',
          desc: '문서가 색인되면 대화에서 {\'@\'}로 이 지식 베이스를 지정해 출처가 포함된 답변을 받을 수 있습니다.'
        },
        upload: {
          title: '문서 추가',
          desc: '여기에서 파일·폴더 업로드, URL 가져오기, 온라인 편집 콘텐츠 생성을 할 수 있습니다.'
        },
        intro: {
          title: '지식 베이스가 비어 있습니다',
          desc: '첫 자료를 추가해야 검색과 대화에 사용할 수 있습니다. 지원 형식은 드래그 앤 드롭으로도 업로드할 수 있습니다.'
        }
      }
    },
    agentCreate: {
      steps: {
        submit: {
          title: '에이전트 저장',
          desc: '강조된 확인 버튼을 눌러 완료하세요. 이후 채팅에서 이 에이전트를 선택할 수 있습니다.'
        },
        navTools: {
          title: '도구 및 MCP(선택)',
          desc: '스마트 추론 모드에서 내장 도구와 MCP로 검색·코드 등을 사용할 수 있습니다.'
        },
        multimodal: {
          title: '첨부 업로드 켜기',
          desc: '이미지·오디오 업로드와 첨부 파싱 규칙을 설정하세요. 이미지 업로드 시 아래에서 VLM을 선택해야 합니다.'
        },
        navMultimodal: {
          title: '첨부 업로드(선택)',
          desc: '채팅에서 이미지, 문서, 오디오 등 첨부를 허용합니다. 이미지 이해에는 시스템 설정의 VLM이 필요합니다.'
        },
        navWebsearch: {
          title: '웹 검색(선택)',
          desc: '최신 정보를 위해 외부 검색을 호출할 수 있게 합니다.'
        },
        knowledge: {
          title: '지식 범위',
          desc: '「전체」는 범용, 「선택」은 특정 도메인, 「없음」은 모델만 또는 웹 검색에 의존합니다.'
        },
        navKnowledge: {
          title: '지식 베이스 연결',
          desc: '에이전트가 검색할 지식 범위를 설정합니다. 기본값은 전체 지식 베이스입니다.'
        },
        model: {
          title: '모델 선택',
          desc: '구성된 대화 모델 중 선택하거나, 먼저 시스템 설정에서 추가하세요.'
        },
        navModel: {
          title: '대화 모델 연결',
          desc: '모든 에이전트에 KnowledgeQA 모델이 추론 엔진으로 필요합니다.'
        },
        name: {
          title: '이름과 설명',
          desc: '알아보기 쉬운 이름을 입력하세요. 스마트 추론 모드는 기본값이 채워질 수 있습니다.'
        },
        agentType: {
          title: '에이전트 유형 선택',
          desc: '프리셋은 시스템 프롬프트, 권장 도구, 지식 범위(Wiki 빌드, 데이터 분석 등)를 자동으로 채웁니다. 시나리오에 맞게 바꾸면 이름·설명도 함께 갱신됩니다.'
        },
        mode: {
          title: '실행 모드 선택',
          desc: '「빠른 답변」은 단순 Q&A용, 「스마트 추론」은 도구와 다단계 사고로 복잡한 작업에 적합합니다.'
        }
      }
    },
    agentList: {
      steps: {
        create: {
          title: '에이전트 만들기',
          desc: '에이전트는 모델·지식 베이스·도구·프롬프트를 묶은 재사용 가능한 어시스턴트입니다. 강조된 「에이전트 생성」을 클릭하세요.'
        }
      }
    },
    kbCreate: {
      steps: {
        submit: {
          title: '지식 베이스 생성',
          desc: '「확인」을 클릭하면 지식 베이스를 생성하지 않고 안내를 마칠 수 있습니다. 준비되면 이름을 입력하고 유형과 모델을 확인한 뒤 「생성」을 클릭하세요.'
        },
        faq: {
          title: 'FAQ 색인',
          desc: 'Q&A 쌍의 색인 방식을 선택합니다. 생성 후 이 페이지에서 FAQ 항목을 추가할 수 있습니다.'
        },
        multimodalVllm: {
          title: 'VLM 모델 선택',
          desc: '멀티모달에는 VLM이 필요합니다. 목록이 비어 있으면 시스템 설정에서 추가하세요.'
        },
        multimodalToggle: {
          title: '멀티모달 파싱 켜기',
          desc: '켜면 이미지가 포함된 업로드를 VLM으로 처리해 검색 품질을 높입니다.'
        },
        navMultimodal: {
          title: '멀티모달/이미지(선택)',
          desc: '차트·스캔·이미지가 많은 문서를 시각 이해가 필요할 때 활성화하세요.'
        },
        storage: {
          title: '스토리지(선택)',
          desc: '원본 파일 저장 위치(로컬 또는 객체 스토리지)입니다. 워크스페이스 기본값을 따르면 됩니다.'
        },
        chunking: {
          title: '청킹(선택)',
          desc: '문서를 검색 단위로 나누는 방식입니다. RAG에 맞춘 기본값을 그대로 쓰면 됩니다.'
        },
        parser: {
          title: '파서 엔진(선택)',
          desc: 'PDF·Office 파일 파싱 방식을 제어합니다. 기본값으로 대부분 충분하며 OCR이 필요할 때 조정하세요.'
        },
        embedding: {
          title: 'Embedding 모델',
          desc: '텍스트를 벡터로 바꿔 의미 검색을 지원합니다. 위의 벡터/키워드 색인과 함께 사용합니다.'
        },
        llm: {
          title: '대화/요약 모델',
          desc: '요약·답변 생성에 사용됩니다. 목록이 비어 있으면 드롭다운에서 설정으로 이동해 모델을 추가하세요.'
        },
        navModels: {
          title: '모델 구성(필수)',
          desc: '모든 지식 베이스에 대화 모델이 필요하며, 검색을 쓰려면 Embedding 모델도 필요합니다. 왼쪽 「모델 구성」을 여세요.'
        },
        indexing: {
          title: '색인 기능',
          desc: '벡터·키워드 검색이 기본으로 켜져 있습니다. Wiki·지식 그래프도 선택할 수 있습니다. 검색 방식은 하나 이상 유지하세요.'
        },
        name: {
          title: '이름 입력',
          desc: '「제품 매뉴얼」「고객 FAQ」처럼 알아보기 쉬운 이름을 입력하세요. 설명은 선택 사항입니다.'
        },
        type: {
          title: '유형 선택',
          desc: '문서 라이브러리는 PDF·Word 등 파일용, FAQ 라이브러리는 질문·답변 쌍용입니다. 생성 후 유형은 변경할 수 없습니다.'
        }
      }
    },
    tenantModels: {
      needChatModelFirst: '에이전트를 만들기 전에 대화 모델(KnowledgeQA)을 추가하세요.',
      stepsAgent: {
        done: {
          title: '이후 에이전트 생성',
          desc: '저장 후 설정을 닫고 「에이전트 생성」을 클릭하세요. 마법사가 모드·지식 베이스·첨부 업로드 옵션을 안내합니다.'
        },
        addModel: {
          title: '대화 모델 추가',
          desc: '「모델 추가」를 눌러 KnowledgeQA 유형을 구성하세요.'
        },
        intro: {
          title: '먼저 대화 모델을 구성하세요',
          desc: '에이전트 생성에는 KnowledgeQA 모델이 최소 하나 필요합니다. 시스템 설정에서 추가하세요(Embedding은 지식 베이스에만 필요).'
        }
      },
      steps: {
        done: {
          title: '추가 후 계속',
          desc: '모델을 저장하고 설정을 닫은 뒤 「새 지식 베이스」를 클릭하세요. 마법사가 유형·색인·모델 연결을 안내합니다.'
        },
        addModel: {
          title: '모델 추가',
          desc: '「모델 추가」를 눌러 KnowledgeQA(대화)와 Embedding 유형을 구성하세요. Lite 사용자는 Ollama로 로컬 모델을 받을 수 있습니다.'
        },
        intro: {
          title: '먼저 모델을 구성하세요',
          desc: '문서 지식 베이스에는 대화 모델(요약·Q&A)과 Embedding 모델(벡터 검색)이 각각 하나 이상 필요합니다. 시스템 설정에서 추가하세요.'
        }
      }
    },
    kbList: {
      steps: {
        create: {
          title: '첫 지식 베이스 만들기',
          desc: '지식 베이스에 문서와 FAQ를 보관합니다. 아래에 강조된 「새 지식 베이스」 버튼을 누르면 양식 작성을 안내합니다.'
        }
      }
    }
  },
  newUserGuide: {
    stepOf: '{current} / {total}',
    skip: '건너뛰기',
    prev: '이전',
    next: '다음',
    done: '완료',
    reopen: '사용 가이드',
    steps: {
      done: {
        title: '준비 완료',
        desc: '핵심 기능을 모두 익혔습니다. 이제 나만의 지식 어시스턴트를 만들어 보세요! 메뉴 상단 닉네임 옆 도움말 버튼에서 언제든 가이드를 다시 볼 수 있습니다.'
      },
      models: {
        title: '모델 구성하기',
        desc: '핵심 단계입니다. 모델 관리에서 대화·임베딩 등 모델을 추가해야 지식 베이스와 대화 기능이 정상 작동합니다. \'모델 추가\'를 클릭해 시작하세요.'
      },
      settings: {
        title: '계정 및 설정 입구',
        desc: '여기를 열면 계정, 멤버, 시스템 설정을 관리할 수 있습니다. 이 가이드는 메뉴 상단 닉네임 옆 도움말 버튼에서 다시 열 수 있습니다.'
      },
      agents: {
        title: '전용 에이전트 구축',
        desc: '지식 베이스, 프롬프트, 도구를 결합해 재사용 가능한 에이전트로 전문성을 축적하세요.'
      },
      chat: {
        title: 'AI 대화 시작하기',
        desc: '지식 베이스 내용을 기반으로 질문하고 출처가 포함된 정확한 답변을 받아보세요. 여기를 클릭해 새 대화를 시작하세요.'
      },
      knowledge: {
        title: '지식 베이스 만들기',
        desc: '모든 것의 시작점입니다. 문서, 웹페이지, FAQ를 업로드하면 Xiaozhi가 자동으로 분석하고 색인합니다. 여기를 클릭해 지식 베이스로 이동하세요.'
      },
      welcome: {
        title: 'Xiaozhi에 오신 것을 환영합니다',
        desc: '몇 단계만으로 지식 베이스, 대화, 에이전트의 핵심 사용법을 안내합니다. \'다음\'을 눌러 시작하세요.'
      },
      assistant: {
        title: 'Xiaozhi 어시스턴트를 만나보세요',
        desc: 'Xiaozhi의 버전, 기능, 설정에 대해 질문할 수 있습니다. 현재 페이지를 바탕으로 사용자의 권한 내에서 에이전트를 만들고, 작업을 예약하고, 지식을 정리할 수도 있습니다.'
      }
    }
  },
  assistantEntryGuide: {
    stepOf: 'v0.9.0의 새로운 기능',
    skip: '알겠습니다',
    interactHint: '강조된 아이콘을 클릭해 어시스턴트를 열어 보세요.'
  },
  chatHeader: {
    automationTask: '자동화',
    moreActions: '대화 추가 작업',
    toggleSandboxPanel: '샌드박스 터미널',
    copyMarkdown: 'Markdown으로 복사',
    deleteSession: '대화 삭제',
    renamePlaceholder: '대화 제목을 입력하세요',
    temporaryWorkspace: '임시 작업 영역',
    markdownCopied: '전체 대화가 Markdown으로 복사되었습니다',
    markdownCopyFailed: 'Markdown 복사에 실패했습니다. 다시 시도하세요.',
    clearConfirmTitle: '대화 메시지 지우기',
    clearConfirmBody: '현재 대화의 모든 메시지를 지울까요? 대화는 유지되지만 복구할 수 없습니다.',
    deleteConfirmTitle: '대화 삭제',
    deleteConfirmBody: '현재 대화를 삭제할까요? 삭제 후에는 복구할 수 없습니다.',
    deleteSuccess: '대화가 삭제되었습니다',
    markdown: {
      sessionId: '세션 ID',
      exportedAt: '내보낸 시간',
      user: '사용자',
      assistant: '어시스턴트',
      attachments: '첨부 파일',
      references: '참조'
    },
    grants: {
      menu: '허용된 작업',
      description: '이 대화에서 다시 묻지 않도록 허용된 작업입니다. 취소하면 다음에 다시 묻습니다.',
      empty: '허용된 작업이 없습니다',
      revoke: '취소',
      revoked: '취소되었습니다',
      revokeFailed: '취소하지 못했습니다',
      loadFailed: '불러오지 못했습니다'
    }
  },
  menu: {
    sessionInProgress: '대화 진행 중',
    sessionUnread: '새 답변',
    knowledgeBase: '지식베이스',
    agents: '에이전트',
    automations: '자동화',
    artifacts: '산출물',
    organizations: '공유 공간',
    newChat: '새 대화',
    settings: '시스템 설정',
    logout: '로그아웃',
    clearMessages: '메시지 지우기',
    clearMessagesSuccess: '메시지가 지워졌습니다',
    clearMessagesFailed: '메시지 지우기 실패, 나중에 다시 시도해 주세요',
    renameSession: '제목 수정',
    renameSessionSuccess: '제목이 업데이트되었습니다',
    renameSessionFailed: '제목 수정 실패, 나중에 다시 시도해 주세요',
    batchManage: '일괄 관리',
    newSession: '새 세션',
    pin: '고정',
    unpin: '고정 해제',
    pinFailed: '고정 실패, 나중에 다시 시도해 주세요',
    unpinFailed: '고정 해제 실패, 나중에 다시 시도해 주세요',
    search: '검색',
    collapseSidebar: '사이드바 접기',
    expandSidebar: '사이드바 펼치기',
    myChats: '내 대화',
    apiChats: 'API 세션',
    noSessions: '대화가 없습니다'
  },
  resourceSort: {
    title: '정렬',
    updatedTime: '업데이트 시간',
    updatedTimeDescription: '기본 옵션입니다.',
    createdTime: '생성 시간',
    createdTimeDescription: '최근 또는 가장 먼저 생성된 항목을 확인합니다',
    name: '이름',
    nameDescription: '이름을 알고 있는 항목을 빠르게 찾습니다',
    recentlyUpdated: '최근 업데이트',
    earliestUpdated: '오래된 업데이트',
    recentlyCreated: '최근 생성',
    earliestCreated: '가장 먼저 생성',
    nameAscending: 'A–Z',
    nameDescending: 'Z–A'
  },
  artifactLibrary: {
    title: '산출물',
    subtitle: '모든 대화에서 에이전트가 생성한 파일을 한곳에 모아 보여줍니다',
    typeFilter: '유형별 필터',
    searchPlaceholder: '파일 이름 검색',
    total: '파일 {count}개',
    versions: '버전 {count}개',
    preview: '미리보기',
    delete: '삭제',
    deleteTitle: '이 파일을 삭제할까요?',
    deleteConfirm: '「{name}」과(와) 저장된 내용이 영구적으로 삭제되며 복구할 수 없습니다.',
    deleteConfirmVersions: '「{name}」의 {count}개 버전과 저장된 내용이 모두 영구적으로 삭제되며 복구할 수 없습니다.',
    deleted: '파일을 삭제했습니다',
    deleteFailed: '삭제에 실패했습니다. 다시 시도해 주세요.',
    download: '다운로드',
    downloadFailed: '다운로드에 실패했습니다. 잠시 후 다시 시도해 주세요',
    openSession: '대화 열기',
    untitledSession: '제목 없는 대화',
    loadMore: '더 불러오기',
    loadFailed: '산출물을 불러오지 못했습니다',
    retry: '다시 시도',
    clearFilters: '필터 지우기',
    noMatches: {
      title: '일치하는 파일이 없습니다',
      description: '다른 키워드나 파일 유형으로 시도해 보세요'
    },
    empty: {
      title: '아직 산출물이 없습니다',
      description: '대화에서 에이전트에게 보고서, 표, 슬라이드를 만들게 하면 파일이 여기에 표시됩니다'
    },
    groups: {
      today: '오늘',
      yesterday: '어제',
      last7Days: '최근 7일',
      last30Days: '최근 30일',
      earlier: '이전'
    },
    categories: {
      all: '전체',
      document: '문서',
      spreadsheet: '스프레드시트',
      presentation: '프레젠테이션',
      image: '이미지',
      web: '웹 페이지',
      data: '데이터'
    }
  },
  localBrowser: {
    pipOpen: '미리보기 팝업 열기',
    pipReturn: '대화 내 미리보기로 돌아가기',
    pipFailed: '플로팅 창을 열 수 없습니다. 다시 시도해 주세요.',
    captureScreenshot: '스크린샷 캡처',
    navigationIncomplete: '페이지가 요청한 로드 단계에 도달하지 못했습니다. 현재 페이지를 확인하세요.',
    noEntries: '반환된 기록이 없습니다.',
    stopping: '작업 종료 중…',
    elapsedSeconds: '{seconds}초',
    searchInstructionsTitle: '브라우저 검색 지침',
    searchInstructionsDescription: '선호하는 검색 엔진과 검색 URL을 설정합니다.',
    searchInstructionsHint: '저장 후 다음 요청부터 적용됩니다. 비워 두면 기본값을 사용합니다.',
    searchInstructionsReset: '기본값 복원',
    searchInstructionsSaved: '저장됨',
    sourceHint: '이번 요청에서 로컬 브라우저로 웹페이지를 조회하고 조작합니다. 웹 검색, 지식 베이스 및 다른 도구와 함께 사용할 수 있습니다.',
    pressKey: '키 누르기',
    hoverPage: '요소에 마우스 올리기',
    scrollPage: '페이지 스크롤',
    focusElement: '요소에 초점 맞추기',
    blurElement: '초점 해제',
    selectOption: '옵션 선택',
    closeTab: '탭 닫기',
    runScript: '페이지 스크립트 실행',
    readConsole: '콘솔 확인',
    readNetwork: '네트워크 요청 확인',
    resizeWindow: '창 크기 조정',
    emulateDevice: '기기 에뮬레이션',
    actionPending: '브라우저 조작 중…',
    actionRecorded: '브라우저 작업 기록됨',
    untitledTab: '제목 없는 탭',
    contentTruncated: '페이지 내용의 일부만 표시됩니다.',
    controlScope: '이 대화의 브라우저 작업만 제어',
    pauseHint: '브라우저 작업을 중단하고 재개할 수 있도록 페이지를 유지합니다. 대화는 중단하지 않습니다.',
    stopHint: '이 작업에서 만든 탭을 닫고 빌린 탭을 반환합니다. 브라우저와 페어링은 유지합니다.',
    openPage: '페이지 열기',
    switchPage: '페이지 전환',
    readPage: '페이지 확인',
    listTabs: '탭 목록',
    clickPage: '요소 클릭',
    fillPage: '내용 입력',
    waitPage: '페이지 대기',
    openTab: '작업 탭 만들기',
    switchTab: '작업 탭 전환',
    authorizeTab: '탭 권한 요청',
    returnTab: '탭 반환',
    needHelp: '사용자 입력 필요',
    browserAction: '브라우저 작업',
    actionFailed: '미완료',
    actionCompleted: '작업 완료',
    commandBusy: '이전 작업이 실행 중입니다. 완료될 때까지 기다려 주세요.',
    invalidArguments: '브라우저 도구 인수가 잘못되었거나 불완전합니다. 에이전트가 수정해야 합니다.',
    commandInterrupted: '작업이 중단되었습니다. 페이지를 확인한 뒤 미리보기에서 재개하세요.',
    actionFailedHint: '브라우저 작업이 완료되지 않았습니다. 페이지를 확인하고 다시 시도하세요.',
    previewStale: '화면이 갱신되지 않음',
    previewIdle: '마지막 화면 유지 중',
    previewLive: '화면 동기화 중',
    previewLoading: '화면 가져오는 중',
    borrowHint: '사용하려는 페이지로 전환하여 BrowserSkill 확인 창에서 허용 또는 거부를 선택하세요. 허용하면 자동으로 계속됩니다. 작업 계속은 일시 중지만 해제하며 탭 사용을 승인하지 않습니다.',
    helpHint: '인증 또는 권한 승인이 필요합니다. 미리보기를 클릭하여 이동하세요.',
    settingsTitle: '브라우저 연결',
    settingsDescription: 'BrowserSkill로 내 Chrome 또는 Edge를 연결하면 대화에서 실제 웹페이지를 조작할 수 있습니다.',
    openSettings: '연결 설정 열기',
    settingsHint: '도구함에서 BrowserSkill을 연결하면 로컬 브라우저를 사용할 수 있습니다.',
    unavailable: '서버에서 로컬 브라우저가 활성화되지 않았습니다. 관리자에게 문의하세요.',
    source: '브라우저 연결 대상',
    sandbox: '샌드박스 브라우저',
    local: '로컬 브라우저',
    paused: '일시 중지됨',
    connected: '연결됨',
    disconnected: '연결 안 됨',
    resume: '조작 재개',
    pause: '조작 일시 중지',
    start: '작업 시작',
    stop: '브라우저 작업 종료',
    resumeShort: '재개',
    pauseShort: '일시 중지',
    stopShort: '종료',
    pairHint: '확장 프로그램의 연결 설정 → 원격 연결에 페어링 링크를 붙여넣고 서버를 확인하세요. 링크는 5분 동안 한 번만 사용할 수 있습니다.',
    copyPairing: '페어링 링크 복사',
    copied: '복사됨',
    windowHint: '작업은 별도의 브라우저 작업 창에서 실행됩니다. 기존 탭을 빌리려면 권한이 필요합니다.',
    preview: '로컬 브라우저 미리보기',
    waiting: '작업 페이지를 기다리는 중',
    startHint: '브라우저 요청을 보내면 별도의 작업 창이 생성됩니다.',
    revoke: '기기 인증 취소',
    revokeConfirm: '취소하면 다시 연결해야 로컬 브라우저를 사용할 수 있습니다.',
    failed: '작업에 실패했습니다. 다시 시도하세요.',
    productDescription: '에이전트가 브라우저에서 페이지를 열고 내용을 읽고 작업을 수행할 수 있게 해 주는 오픈소스 Chrome / Edge 확장 프로그램입니다.',
    offline: '오프라인',
    notPaired: '연결 설정 필요',
    lastSeen: '최근 연결',
    readyHint: '준비되었습니다. 대화로 돌아가 브라우저 작업을 요청하세요.',
    capabilitiesTitle: '에이전트가 할 수 있는 작업',
    sidebarStatus: '사이드바에 연결 상태 표시',
    reconnectHint: '인증이 저장되어 있습니다. 브라우저와 확장 프로그램을 열면 자동으로 다시 연결됩니다.',
    replaceDevice: '브라우저 변경',
    installExtension: 'BrowserSkill 설치',
    storeInstall: 'Chrome 웹 스토어',
    edgeStoreInstall: 'Edge 추가 기능',
    extensionMinVersion: 'BrowserSkill v{version} 이상이 필요합니다. Chrome과 Edge를 지원합니다.',
    extensionOutdated: '확장 프로그램 v{current}이(가) 오래되었습니다. v{version} 이상으로 업데이트하세요.',
    manualInstall: '수동 설치 (대안)',
    storeInstallHint: 'Chrome 웹 스토어 또는 Edge 추가 기능에서 BrowserSkill을 설치한 후 여기로 돌아와 페어링하세요.',
    installHint: '스토어에 접근할 수 없거나 버전이 호환되지 않으면 호환 패키지를 다운로드하여 수동으로 설치할 수 있습니다.',
    downloadExtension: '호환 패키지 다운로드',
    officialExtension: '공식 확장 프로그램 (Chrome 웹 스토어)',
    installGuide: '다운로드한 패키지는 어떻게 설치하나요?',
    pairGuide: '페어링 링크는 어떻게 사용하나요?',
    pairBrowser: '브라우저 연결',
    packageUnavailable: '관리자에게 호환되는 확장 프로그램 패키지를 요청하세요.',
    manualCopy: '아래 링크를 복사하세요. 5분 동안 한 번만 사용할 수 있습니다.',
    pairingReady: '복사되었습니다. 5분 안에 확장 프로그램에 붙여넣으세요. 한 번만 사용할 수 있습니다.',
    copyAgain: '다시 복사',
    usageTitle: '사용 방법',
    usageStep1Title: '확장 프로그램 설치',
    usageStep1Text: 'ZIP 파일의 압축을 풀고 브라우저 주소창에 chrome://extensions(Edge는 edge://extensions)를 입력하세요. 개발자 모드를 켜고 압축해제된 확장 프로그램을 로드합니다를 선택한 뒤 압축을 푼 확장 프로그램 폴더를 선택하세요.',
    usageStep2Title: '브라우저 연결',
    usageStep2Text: '페어링 링크를 확장 프로그램의 연결 설정 → 원격 연결에 붙여넣고 서버를 확인하세요. 한 번 연결하면 공간 내 모든 대화에서 공유됩니다.',
    usageStep3Title: '대화에서 작업 요청',
    usageStep3Text: '웹 작업을 보내기 전에 대화 입력창에서 로컬 브라우저를 켜세요. 페어링만으로 자동 활성화되지는 않습니다. 작업은 별도의 작업 창에서 실행됩니다.',
    usageStep4Title: '미리보기로 확인하고 이어가기',
    usageStep4Text: '대화에 작은 미리보기가 나타납니다. 클릭하면 작업 탭으로 이동합니다. 중단된 작업은 다시 연결해도 일시정지 상태이므로 미리보기에서 계속하세요. 기존 탭에는 권한이 필요합니다.',
    running: '실행 중',
    locateWindow: '브라우저 표시',
    reconnectShort: '재연결 대기 중'
  },
  toolbox: {
    title: '도구함',
    unavailable: '현재 워크스페이스에서 사용할 수 있는 도구가 없습니다.'
  },
  automation: {
    conversationNotice: '자동화 작업이 실행하는 대화입니다. 메시지를 직접 보낼 수 없습니다. 대기 중인 요청은 위에서 처리하세요.'
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
