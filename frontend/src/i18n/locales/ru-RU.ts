export default {
  memorySettings: {
    kinds: {
      profile: 'О вас',
      preference: 'Предпочтение',
      fact: 'Факт',
      task: 'Текущая задача',
      interest: 'Долгосрочный интерес'
    },
    usage: {
      title: 'Когда записи используются'
    }
  },
  imagePipeline: {
    smartocr: {
      name: 'Умный',
      description: 'Сначала наблюдаются признаки изображения и создаётся его описание, затем по этим признакам решается, вызывать ли OCR. Экономит вызовы модели и ускоряет разбор Если изображение распознано как фотография выравниваемой страницы или этикетки, перед распознаванием оно автоматически выравнивается и обрезается для повышения точности OCR; при неудаче используется исходное изображение.',
      ocr: {
        thinking_enabled: {
          label: 'С размышлением при распознавании текста',
          description: 'Дать модели поразмышлять перед расшифровкой текста. Как правило, в этом нет необходимости: включение размышлений замедляет обработку и слишком длинные размышления могут вытеснить основной текст, из-за чего задача завершится неудачей. Включайте только если вы уверены, что это необходимо.'
        }
      },
      observation: {
        thinking_enabled: {
          label: 'С размышлением при описании',
          description: 'Дать модели поразмышлять перед описанием изображения и отчётом о его признаках. Как правило, в этом нет необходимости: включение размышлений замедляет обработку и слишком длинные размышления могут вытеснить основной текст, из-за чего задача завершится неудачей. Включайте только если вы уверены, что это необходимо.'
        }
      },
      preprocess: {
        mode: {
          label: 'Предобработка документа',
          description: 'По умолчанию выключено. Выравнивание и обрезка перед OCR увеличивают время обработки. Авто: по результатам наблюдения; Всегда: для всех изображений, выбранных для OCR. При занятости или превышении лимитов используется оригинал.',
          options: {
            auto: 'Авто',
            off: 'Выкл.',
            always: 'Всегда'
          }
        }
      },
      note_flow: {
        label: 'Решает наблюдение',
        description: 'Сначала изображение описывается и наблюдается, и полученные атрибуты решают, стоит ли тратить на него ещё один проход OCR. Если они говорят, что страницу нужно выпрямить, её выпрямляют и обрезают окружающий фон перед чтением; если этот шаг недоступен или отказывается, читается исходный снимок — хуже не будет.'
      },
      ocr_on_unobserved: {
        label: 'Запускать OCR при сбое наблюдения атрибутов изображения',
        description: 'Если модель не смогла корректно наблюдать атрибуты изображения, OCR по умолчанию всё равно выполняется, чтобы не потерять текст; выключите, чтобы пропустить. (Небольшая визуальная модель вроде 4B или пользовательские инструкции к изображениям, конфликтующие с системным промптом, могут привести к сбою наблюдения; модели 8B и выше ошибаются редко, поэтому отключать не рекомендуется)'
      }
    },
    default: {
      name: 'Ручной',
      description: 'Пользователь сам включает или выключает действия разбора под задачу.',
      ocr: {
        thinking_enabled: {
          label: 'С размышлением при распознавании',
          description: 'Дать модели поразмышлять перед расшифровкой текста. Как правило, в этом нет необходимости: включение размышлений замедляет обработку и слишком длинные размышления могут вытеснить основной текст, из-за чего задача завершится неудачей. Включайте только если вы уверены, что это необходимо.'
        }
      },
      caption: {
        thinking_enabled: {
          label: 'С размышлением при описании',
          description: 'Дать модели поразмышлять перед тем, как писать описание. Как правило, в этом нет необходимости: включение размышлений замедляет обработку и слишком длинные размышления могут вытеснить основной текст, из-за чего задача завершится неудачей. Включайте только если вы уверены, что это необходимо.'
        }
      },
      ocr_enabled: {
        label: 'Распознавание текста',
        description: 'Извлекает текст, присутствующий на изображении.'
      },
      caption_enabled: {
        label: 'Описание изображения',
        description: 'Генерирует однострочное описание каждого изображения и сохраняет его как подпись.'
      },
      note_actions: {
        label: 'Два действия независимы',
        description: 'Каждое включается отдельно: без OCR изображение всё равно описывается, без описания его текст всё равно распознаётся. Только выключив оба, изображение остаётся необработанным — поэтому панель запрещает такую комбинацию.'
      }
    },
    errors: {
      noActionEnabled: 'Включите хотя бы одно действие разбора, иначе ничего не будет обработано.'
    }
  },
  imageAttr: {
    layout_upright: {
      label: 'Ориентация текста',
      description: 'Читается ли текст в нормальном положении. Повёрнутую или перевёрнутую страницу стоит выпрямить перед OCR.',
      values: {
        false: {
          label: 'Повёрнут',
          description: 'текст повёрнут, наклонён или перевёрнут'
        },
        true: {
          label: 'Прямо',
          description: 'текст в обычной ориентации'
        }
      }
    },
    layout_margin: {
      label: 'Поля вокруг текста',
      description: 'Какая часть кадра занята не текстом (стол, фон, пустое место). Большие поля означают, что страницу можно обрезать плотнее перед OCR.',
      values: {
        large: {
          label: 'Много',
          description: 'много места без текста: стол, комната, почти пустая страница'
        },
        small: {
          label: 'Мало',
          description: 'узкая полоса фона'
        },
        none: {
          label: 'Нет',
          description: 'текст доходит до краёв'
        }
      }
    },
    contain_data_visual: {
      label: 'Визуализация данных',
      description: 'Передаёт ли изображение данные в виде графика, диаграммы, схемы или инфографики. Такие изображения остаются в очереди OCR, даже если текста на вид немного.',
      values: {
        false: {
          label: 'Нет',
          description: 'нет —— фото, рисунок, значок или декор'
        },
        true: {
          label: 'Да',
          description: 'да —— график, диаграмма или схема'
        }
      }
    },
    contain_text: {
      label: 'Количество текста на изображении',
      description: 'Сколько основного текста содержит само изображение. Определяет, стоит ли запускать для него отдельный проход OCR.',
      values: {
        block: {
          label: 'Блок текста',
          description: 'блок основного текста —— скриншот, таблица, страница документа'
        },
        sparse: {
          label: 'Немного текста',
          description: 'несколько слов —— логотип, дорожный знак, одна надпись'
        },
        none: {
          label: 'Нет текста',
          description: 'текста нет'
        }
      }
    }
  },
  tenantInvitation: {
    errors: {
      notPending: 'The invitation is no longer pending.',
      forbidden: 'Only the invitee can accept or decline this invitation.',
      notFound: 'Invitation not found or already withdrawn.',
      generic: 'Something went wrong. Please try again.'
    },
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
    }
  },
  tenantMember: {
    title: 'Участники',
    loading: 'Загрузка участников…',
    retry: 'Повторить',
    audit: {
      action: {
        'rbac.member_added': 'Добавлен участник',
        'rbac.member_removed': 'Удалён участник',
        'rbac.member_role_changed': 'Изменение роли',
        'rbac.member_left': 'Участник вышел',
        'rbac.access_denied': 'Доступ запрещён',
        'rbac.invitation_sent': 'Приглашение отправлено',
        'rbac.invitation_accepted': 'Приглашение принято',
        'rbac.invitation_declined': 'Приглашение отклонено',
        'rbac.invitation_revoked': 'Приглашение отозвано',
        'rbac.invitation_expired': 'Приглашение истекло'
      }
    },
    errors: {
      lastOwner: 'Нельзя понизить, удалить или покинуть как последний Владелец. Сначала повысьте кого-то ещё до Владельца.',
      generic: 'Что-то пошло не так. Попробуйте ещё раз.'
    },
    leave: {
      confirmTitle: 'Покинуть это пространство?',
      confirmBody: 'Вы потеряете доступ ко всем базам знаний и агентам в этом пространстве. Позже вас можно будет пригласить снова.',
      confirm: 'Покинуть',
      success: 'Вы покинули пространство'
    },
    role: {
      owner: 'Владелец',
      admin: 'Администратор',
      contributor: 'Участник',
      viewer: 'Наблюдатель'
    },
    permissions: {
      title: 'Права ролей',
      desc: 'Что может делать каждая роль внутри этого пространства. Контролируется сервером; элементы UI лишь отражают правила.'
    }
  },
  userProfile: {
    title: 'Информация о пользователе',
    description: 'Просмотр базовых данных аккаунта (ID пользователя, имя, логин, дата регистрации) и смена пароля.',
    changePassword: {
      label: 'Сменить пароль',
      description: 'Подтвердите текущий пароль и задайте новый. После успешной смены все сессии будут отозваны, потребуется повторный вход.',
      currentLabel: 'Текущий пароль',
      currentPlaceholder: 'Введите текущий пароль',
      currentRequired: 'Введите текущий пароль',
      newLabel: 'Новый пароль',
      newPlaceholder: 'Введите новый пароль',
      confirmLabel: 'Подтвердите новый пароль',
      confirmPlaceholder: 'Введите новый пароль ещё раз',
      submit: 'Обновить пароль',
      success: 'Пароль обновлён. Войдите снова с новым паролем.',
      failed: 'Не удалось сменить пароль. Проверьте текущий пароль.',
      policyFailed: 'Новый пароль: 8–32 символа, буквы и цифры',
      sameAsCurrent: 'Новый пароль не должен совпадать с текущим',
      oidcOnlyDescription: 'Аккаунт создан через OIDC; локальный пароль ещё не задан.'
    }
  },
  credential: {
    configured: 'Настроено',
    unconfigured: 'Не настроено',
    configure: 'Настроить',
    update: 'Заменить',
    remove: 'Удалить',
    inputPlaceholder: 'Введите значение',
    savedToast: 'Учётные данные сохранены',
    saveFailed: 'Не удалось сохранить учётные данные',
    removedToast: 'Учётные данные удалены',
    removeFailed: 'Не удалось удалить учётные данные',
    confirmRemovePrompt: 'Удалить учётные данные? Действие необратимо.',
    confirmRemove: 'Подтвердить удаление'
  },
  integrations: {
    claw: {
      title: 'WeKnora Skill'
    },
    chrome: {
      title: 'Помощник по знаниям'
    },
    agentEditor: {
      desc: 'Публикуйте агента в IM или на сайт. Управление — в разделе «Интеграции».'
    },
    embedOverview: {
      title: 'Каналы веб-встраивания'
    },
    imOverview: {
      title: 'Подключённые IM-каналы'
    },
    api: {
      title: 'API-интеграция',
      updateApiKeyScopeFailed: 'Не удалось обновить API key'
    },
    tabs: {
      im: 'IM-интеграция',
      embed: 'Веб-встраивание',
      api: 'API-интеграция',
      chrome: 'Расширение Chrome',
      cli: 'CLI',
      claw: 'Claw Skill',
      mcpserver: 'MCP-сервер'
    },
    mcpserver: {
      title: 'MCP-сервер',
      tools: {
        list_knowledge_bases: 'Список баз знаний',
        list_knowledge_basesDesc: 'Возвращает базы знаний в области и поддерживаемые режимы поиска',
        search_knowledge: 'Семантический поиск',
        search_knowledgeDesc: 'Находит релевантные фрагменты по вопросу на естественном языке, с источниками',
        grep_chunks: 'Поиск по ключевым словам / regex',
        grep_chunksDesc: 'Регистронезависимый regex по исходным фрагментам; подходит для точных терминов, кодов и имён',
        list_documents: 'Список документов',
        list_documentsDesc: 'Постраничный список документов одной базы знаний',
        read_document: 'Прочитать документ',
        read_documentDesc: 'Метаданные документа и его фрагменты по порядку',
        ask: 'Задать вопрос',
        askDesc: 'Запускает агента, настроенного на конечной точке, и возвращает ответ с цитатами; поддерживает продолжение диалога',
        wiki_search: 'Поиск по Wiki',
        wiki_searchDesc: 'Поиск по сгенерированным страницам Wiki',
        wiki_read_page: 'Прочитать страницу Wiki',
        wiki_read_pageDesc: 'Читает одну страницу Wiki по slug',
        wiki_index: 'Оглавление Wiki',
        wiki_indexDesc: 'Показывает оглавление Wiki базы знаний',
        add_document: 'Добавить документ',
        add_documentDesc: 'Добавляет документ из Markdown-текста или по URL',
        update_document: 'Обновить документ',
        update_documentDesc: 'Заменяет содержимое или заголовок Markdown-документа',
        delete_document: 'Удалить документ',
        delete_documentDesc: 'Безвозвратно удаляет документ и его индекс'
      },
      groups: {
        retrieve: 'Поиск и чтение',
        chat: 'Вопросы и ответы',
        wiki: 'Wiki',
        ingest: 'Запись (включайте осторожно)'
      }
    },
    cli: {
      title: 'WeKnora CLI'
    }
  },
  datasource: {
    title: 'Источники данных',
    description: 'Настройте внешние источники данных для автоматической синхронизации контента',
    add: 'Добавить источник',
    empty: 'Источники данных не настроены',
    edit: 'Редактировать',
    delete: 'Удалить',
    deleteConfirm: 'Удалить этот источник данных? Синхронизированные знания не будут удалены.',
    deleteSuccess: 'Источник данных удалён',
    deleteFailed: 'Не удалось удалить',
    syncNow: 'Синхронизировать',
    syncTriggered: 'Задача синхронизации отправлена',
    syncFailed: 'Не удалось запустить синхронизацию',
    pause: 'Пауза',
    resume: 'Возобновить',
    paused: 'Приостановлено',
    resumed: 'Возобновлено',
    pauseFailed: 'Не удалось приостановить',
    logs: 'Журнал',
    syncModeLabel: 'Режим синхронизации',
    parseModeLabel: 'Режим разбора',
    parseModeHint: 'Способ разбора облачных документов Feishu. Блочный разбор быстрее и сохраняет вложения документа; экспорт преобразует документ в docx и лучше сохраняет связь изображений с документом.',
    createTitle: 'Добавить источник данных',
    editTitle: 'Редактировать источник данных',
    nameLabel: 'Название',
    namePlaceholder: 'Введите название источника данных',
    sectionBasic: 'Основная информация',
    testConnection: 'Проверить подключение',
    testSuccess: 'Подключение успешно',
    testFailed: 'Подключение не удалось',
    connected: 'Подключено',
    connectionFailed: 'Подключение не удалось',
    isRequired: 'обязательно для заполнения',
    credentialsLabel: 'учётные данные',
    resourceHint: 'Выберите пространства или папки для синхронизации',
    untitled: 'Без названия',
    resourceLoadFailed: 'Не удалось загрузить список ресурсов',
    noResources: 'Пространства вики не найдены',
    noResourcesDesc: 'Приложению требуется доступ к вики через групповой чат для получения контента',
    noResourcesDesc_notion: 'Приложению требуются права доступа к странице Notion для получения контента',
    retryLoadResources: 'Повторить',
    guideStep1: 'Создайте групповой чат в Feishu, затем добавьте ваше приложение как бота в настройках группы',
    guideStep2: 'Откройте вики "Настройки" > "Управление участниками" > "Добавить участника", найдите групповой чат и добавьте его',
    guideStep3: 'Убедитесь, что роль группового чата как минимум "Может читать", затем вернитесь и нажмите Повторить',
    guideStep1_notion: 'Откройте страницу или базу данных, которую хотите синхронизировать в Notion',
    guideStep2_notion: 'Нажмите меню «···» в правом верхнем углу, выберите «Connect to» или «Add connections»',
    guideStep3_notion: 'Найдите и выберите ваше интеграционное приложение, затем вернитесь и нажмите Повторить',
    noResourcesDesc_nextcloud: 'Нет доступных папок или поддерживаемых файлов',
    guideStep1_nextcloud: 'Войдите в Nextcloud и проверьте права чтения выбранных папок',
    guideStep2_nextcloud: 'Создайте пароль приложения в разделе «Личные настройки → Безопасность → Устройства и сеансы»',
    guideStep3_nextcloud: 'Замените учётные данные здесь и повторите загрузку ресурсов',
    noResourcesDesc_seafile: 'Токену недоступна ни одна библиотека, либо все библиотеки зашифрованы (зашифрованные библиотеки не синхронизируются)',
    guideStep1_seafile: 'Войдите в Seafile и убедитесь, что у аккаунта есть доступ на чтение хотя бы к одной незашифрованной библиотеке',
    guideStep2_seafile: 'Создайте или пересоздайте токен в разделе «Настройки → Web API токен»',
    guideStep3_seafile: 'Вернитесь сюда, введите новый токен и нажмите Повторить',
    permissionDocLink: 'Документация по настройке прав доступа',
    syncScheduleLabel: 'Расписание синхронизации',
    conflictLabel: 'Стратегия конфликтов',
    syncDeletions: 'Синхронизировать удаления (удалять знания при удалении в источнике)',
    createAndSync: 'Создать и синхронизировать',
    createAndSyncSuccess: 'Источник данных создан, задача синхронизации поставлена в очередь',
    createButSyncFailed: 'Источник данных создан, но не удалось запустить синхронизацию',
    updateSuccessSyncHint: 'Источник данных обновлён. Редактирование не запускает синхронизацию автоматически; нажмите «Синхронизировать», чтобы импортировать изменения.',
    saveFailed: 'Не удалось сохранить',
    syncHistory: 'История синхронизации',
    refreshLogs: 'Обновить журнал',
    noLogs: 'Нет записей синхронизации',
    comingSoon: 'Скоро',
    docHint: 'Получить учётные данные можно здесь:',
    openDoc: 'Открыть документацию',
    prereqBarText: 'Используете впервые? Нажмите, чтобы открыть руководство по настройке приложения Feishu',
    prereqBarText_yuque: 'Используете впервые? Нажмите, чтобы открыть руководство по настройке Yuque Token',
    prereqStep1Brief_yuque: 'Создайте персональный Yuque Token',
    prereqStep1Desc_yuque: 'Войдите в Yuque → значок профиля → Настройки → Token → Создать новый Token',
    prereqStep2Brief_yuque: 'Назначьте Token необходимые права',
    prereqStep2Desc_yuque: 'Выберите как минимум repo:read и doc:read (чтение баз знаний и содержимого документов)',
    prereqStep3Brief_yuque: '(Опционально) Для Enterprise укажите Base URL',
    prereqStep3Desc_yuque: 'Пользователям публичного облака указывать не нужно. Для Yuque Enterprise или приватного развёртывания укажите корпоративный домен',
    prereqStep1Brief_feishu: 'Создать частное приложение Feishu',
    prereqStep1Desc_feishu: 'Войдите в Feishu Open Platform → Создать корпоративное частное приложение',
    prereqStep2Brief_feishu: 'Добавить возможность бота',
    prereqStep2Desc_feishu: 'Open Platform → Ваше приложение → Добавить возможность приложения → Bot',
    prereqStep3Brief_feishu: 'Настроить разрешения приложения',
    prereqStep3Desc_feishu: 'Включите разрешения: wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly',
    prereqStep1Brief_lark: 'Создать частное приложение Lark',
    prereqStep1Desc_lark: 'Войдите в Lark Open Platform → Создать корпоративное частное приложение',
    prereqStep2Brief_lark: 'Добавить возможность бота',
    prereqStep2Desc_lark: 'Open Platform → Ваше приложение → Добавить возможность приложения → Bot',
    prereqStep3Brief_lark: 'Настроить разрешения приложения',
    prereqStep3Desc_lark: 'Включите разрешения: wiki:wiki:readonly, drive:drive:readonly, drive:export:readonly, docx:document:readonly',
    prereqStep1Brief_feishu_drive: 'Создать частное приложение Feishu',
    prereqStep1Desc_feishu_drive: 'Войдите в Feishu Open Platform → Создать корпоративное частное приложение',
    prereqStep2Brief_feishu_drive: 'Добавить возможность бота',
    prereqStep2Desc_feishu_drive: 'Open Platform → Ваше приложение → Добавить возможность приложения → Bot',
    prereqStep3Brief_feishu_drive: 'Настроить разрешения приложения',
    prereqStep3Desc_feishu_drive: 'Включите разрешения: drive:drive:readonly, drive:export:readonly, docx:document:readonly',
    prereqStep1Brief_lark_drive: 'Создать частное приложение Lark',
    prereqStep1Desc_lark_drive: 'Войдите в Lark Open Platform → Создать корпоративное частное приложение',
    prereqStep2Brief_lark_drive: 'Добавить возможность бота',
    prereqStep2Desc_lark_drive: 'Open Platform → Ваше приложение → Добавить возможность приложения → Bot',
    prereqStep3Brief_lark_drive: 'Настроить разрешения приложения',
    prereqStep3Desc_lark_drive: 'Включите разрешения: drive:drive:readonly, drive:export:readonly, docx:document:readonly',
    prereqOpenConsole_yuque: 'Перейти к настройкам Yuque Token',
    yuqueFolderModeLabel: 'Структура папок',
    yuqueFolderModeToc: 'Как в оглавлении Yuque',
    yuqueFolderModeNone: 'Всё в корне',
    yuqueFolderModeHint: 'Раскладывает документы по папкам согласно оглавлению Yuque. Обратите внимание: папки, перемещённые вручную в базе знаний, будут перезаписаны структурой Yuque при следующей синхронизации этого документа.',
    yuqueTOCOnly: 'Синхронизировать только видимые в оглавлении Yuque документы',
    yuqueTOCOnlyHint: 'Требуется режим «Как в оглавлении Yuque». Документы, уже добавленные в базу знаний, остаются нетронутыми — документ, которого нет в оглавлении Yuque, просто перестаёт добавляться, но не удаляется.',
    dingtalkIngestLabel: 'Область импорта DingTalk',
    dingtalkIncludeUploadedFiles: 'Импортировать загруженные файлы (docx / pptx / xlsx / pdf)',
    dingtalkIncludeUploadedFilesHint: 'По умолчанию выключено. Если включено, файлы Word / PowerPoint / Excel / PDF, загруженные в выбранную область, скачиваются и разбираются в базу знаний — до 64 МиБ на файл; их текст учитывается в расходах на хранение и эмбеддинги. Если выключено, они просто пропускаются: в журнале синхронизации указывается, что переключатель не включён, а уже загруженные копии сохраняются.',
    prereqBarText_dingtalk: 'Используете впервые? Откройте руководство по настройке приложения DingTalk',
    prereqStep1Brief_dingtalk: 'Создайте внутреннее корпоративное приложение',
    prereqStep1Desc_dingtalk: 'Создайте внутреннее приложение в DingTalk Open Platform и скопируйте Client ID и Client Secret.',
    prereqStep2Brief_dingtalk: 'Предоставьте права чтения базы знаний',
    prereqStep2Desc_dingtalk: 'Предоставьте права Wiki.Workspace.Read, Wiki.Node.Read и Storage.File.Read.',
    prereqStep3Brief_dingtalk: 'Укажите Union ID оператора',
    prereqStep3Desc_dingtalk: 'Укажите Union ID пользователя DingTalk, у которого есть доступ к целевым базам знаний.',
    prereqOpenConsole_dingtalk: 'Открыть консоль разработчика DingTalk',
    prereqBarText_ima: 'В первый раз? Нажмите, чтобы увидеть руководство по настройке Tencent IMA OpenAPI',
    prereqStep1Brief_ima: 'Включите доступ к IMA agent OpenAPI',
    prereqStep1Desc_ima: 'Войдите на https://ima.qq.com/agent-interface и подайте заявку на доступ к OpenAPI',
    prereqStep2Brief_ima: 'Получите ClientID и APIKey',
    prereqStep2Desc_ima: 'Скопируйте учётные данные ima-openapi-clientid и ima-openapi-apikey на странице agent-interface',
    prereqStep3Brief_ima: 'Предоставьте учётным данным доступ к целевым базам знаний',
    prereqStep3Desc_ima: 'В клиенте IMA авторизуйте учётные данные для баз знаний, которые нужно синхронизировать; неавторизованные базы в списке не отобразятся',
    prereqOpenConsole_ima: 'Открыть консоль Tencent IMA OpenAPI',
    prereqBotBrief: 'Добавьте приложению возможность «Бот»',
    prereqBotDesc: 'Открытая платформа → Добавить возможность приложения → Бот → Создать версию и опубликовать',
    prereqPermBrief: 'Включите права API',
    prereqOpenConsole: 'Открыть настройки Feishu Open Platform',
    prereqMemberBrief: 'Добавьте через групповой чат как участника базы знаний',
    prereqMemberDesc: 'Создайте групповой чат → добавьте приложение как группового бота → добавьте групповой чат как участника базы знаний',
    back: 'Назад',
    next: 'Далее',
    save: 'Сохранить',
    schedule30min: 'Каждые 30 мин',
    schedule1h: 'Каждый час',
    schedule6h: 'Каждые 6 часов',
    schedule12h: 'Каждые 12 часов',
    schedule24h: 'Ежедневно',
    neverSynced: 'Не синхронизировано',
    justNow: 'Только что',
    minutesAgo: '{n} мин назад',
    hoursAgo: '{n} ч назад',
    daysAgo: '{n} д назад',
    syncError: {
      dingtalk_document_failed: 'Не удалось прочитать документ DingTalk. Проверьте права доступа и повторите синхронизацию.',
      dingtalk_document_too_large: 'Файл DingTalk превышает лимит загрузки 64 MiB и пропущен в этой синхронизации. Сожмите или разделите файл.',
      dingtalk_resource_failed: 'Ресурс DingTalk недоступен. Проверьте права доступа и выбранные ресурсы, затем повторите попытку.',
      deletion_lookup_failed: 'Не удалось найти элемент перед удалением; подробности в журнале сервера',
      deletion_failed: 'Не удалось удалить элемент; подробности в журнале сервера',
      ingest_failed: 'Не удалось импортировать элемент; подробности в журнале сервера',
      nextcloud_permission_denied: 'Нет доступа к файлу Nextcloud. Проверьте права учётной записи.',
      nextcloud_not_found: 'Файл Nextcloud исчез после получения списка. Следующая синхронизация повторит попытку.',
      nextcloud_file_too_large: 'Файл Nextcloud превышает ограничение MAX_FILE_SIZE_MB.',
      nextcloud_empty_file: 'Пустой файл Nextcloud пропущен.',
      nextcloud_source_changed: 'Файл Nextcloud изменился во время загрузки. Следующая синхронизация повторит попытку.',
      nextcloud_invalid_response: 'Nextcloud вернул неверный или неполный ответ WebDAV.',
      nextcloud_ssrf_blocked: 'Политика SSRF заблокировала запрос Nextcloud. Проверьте SSRF_WHITELIST.',
      nextcloud_fetch_failed: 'Не удалось получить файл Nextcloud. Следующая синхронизация повторит попытку.',
      seafile_permission_denied: 'Доступ к файлу Seafile запрещён. Проверьте права владельца токена на библиотеку.',
      seafile_not_found: 'Файл Seafile не существует или был перемещён; при следующей синхронизации попытка повторится.',
      seafile_file_too_large: 'Файл Seafile превышает ограничение размера. Увеличьте MAX_FILE_SIZE_MB или уменьшите файл.',
      seafile_empty_file: 'Файл Seafile пуст и был пропущен.',
      seafile_source_changed: 'Файл Seafile изменился во время получения; при следующей синхронизации попытка повторится.',
      seafile_invalid_response: 'Seafile вернул ответ, который не удалось разобрать. Проверьте версию сервера и обратный прокси.',
      seafile_ssrf_blocked: 'URL скачивания Seafile заблокирован политикой SSRF. Добавьте хост fileserver в SSRF_WHITELIST.',
      seafile_fetch_failed: 'Не удалось получить файл из Seafile; при следующей синхронизации попытка повторится.'
    },
    resourceType: {
      wikiSpace: 'Пространство вики',
      docCategory: 'Тег документа',
      book: 'База знаний Yuque',
      library: 'Библиотека Seafile'
    },
    scheduleHuman: {
      '30min': 'Каждые 30 мин',
      '1h': 'Каждый час',
      '6h': 'Каждые 6 часов',
      '12h': 'Каждые 12 часов',
      '24h': 'Ежедневно'
    },
    confluence: {
      cloudFolderLimitation: 'Confluence Cloud пока не может показать здесь страницы из папок верхнего уровня пространства; при выборе всего пространства они будут синхронизированы.'
    },
    field: {
      appId: 'App ID',
      appSecret: 'App Secret',
      clientId: 'Client ID',
      clientSecret: 'Client Secret',
      operatorId: 'Union ID оператора',
      operatorIdHint: 'Укажите Union ID пользователя DingTalk, у которого есть доступ к целевым базам знаний.',
      integrationToken: 'Integration Token',
      apiToken: 'API Token',
      confluenceEdition: 'Версия Confluence',
      confluenceEditionServer: 'Server / Data Center',
      confluenceEditionCloud: 'Cloud',
      confluenceBaseUrl: 'URL Confluence',
      confluenceUsername: 'Имя пользователя или эл. почта',
      confluencePat: 'Персональный токен Server/DC (PAT)',
      confluencePatHint: 'Необязательно. При указании используется Bearer-аутентификация; имя пользователя и пароль не требуются.',
      confluencePassword: 'Пароль Server/DC',
      confluenceApiToken: 'API-токен Cloud',
      imaClientId: 'IMA ClientID',
      imaApiKey: 'IMA APIKey',
      baseUrl: 'Base URL',
      baseUrlHint: 'Оставьте пустым, чтобы использовать адрес общедоступного облака по умолчанию. Для частных/корпоративных развертываний или при доступе через обратный прокси введите ваш собственный адрес (например, https://api-proxy.example.com)',
      feedUrls: 'Адреса лент',
      feedUrlsHint: 'По одному адресу ленты RSS / Atom в строке; можно указать несколько.',
      authHeaders: 'Пользовательские заголовки (необязательно)',
      authHeadersHint: 'Для приватных лент. По одному в строке в формате «Имя: Значение», например Authorization: Bearer xxxx'
    },
    drive: {
      folderTokenLabel: 'Токен папки Drive',
      folderTokenPlaceholder: 'Введите folder_token или URL папки Feishu Drive',
      folderTokenRequired: 'Введите конкретный folder_token; корень облачного пространства не поддерживается',
      rootNotSupportedHint: 'Корневая папка не поддерживает постраничный вывод и не возвращает ярлыки; выберите конкретную папку',
      load: 'Загрузить',
      shareHint: 'Сначала поделитесь папкой Drive с группой приложения, иначе приложение не получит к ней доступ',
      placeholderTitle: 'Сначала загрузите папку Drive',
      placeholderDesc: 'Введите выше folder_token (или вставьте URL папки Feishu Drive) и нажмите «Загрузить»',
      loadForbiddenHint: 'У приложения нет доступа к этой папке. Поделитесь папкой с группой приложения в Feishu Drive и повторите.',
      loadAuthHint: 'Учётные данные приложения недействительны или отсутствуют области Drive. Проверьте App ID / App Secret и разрешения drive:drive:readonly.',
      loadNotFoundHint: 'folder_token не существует или удалён. Проверьте токен, скопированный из URL папки Feishu Drive.'
    },
    connectorDesc: {
      feishu: 'Синхронизация документов, таблиц и файлов из Feishu Wiki',
      lark: 'Синхронизация документов, таблиц и файлов из Lark Wiki',
      feishu_drive: 'Синхронизация документов, таблиц и файлов из папки Feishu Drive',
      lark_drive: 'Синхронизация документов, таблиц и файлов из папки Lark Drive',
      notion: 'Синхронизация страниц и баз данных из Notion',
      confluence: 'Синхронизация пространств и страниц Confluence в Markdown',
      yuque: 'Синхронизация документов из баз знаний Yuque',
      dingtalk: 'Синхронизация онлайн-документов из баз знаний DingTalk',
      rss: 'Синхронизация статей из лент RSS / Atom',
      ima: 'Синхронизация документов, заметок и файлов из баз знаний Tencent IMA (ИИ-сессии и разбор видео не поддерживаются)',
      gitlab: 'Синхронизация файлов из проектов GitLab',
      nextcloud: 'Синхронизация папок и файлов Nextcloud через WebDAV',
      seafile: 'Синхронизация папок и файлов из библиотек Seafile'
    },
    connector: {
      feishu: 'Feishu (Фэйшу)',
      lark: 'Lark',
      feishu_drive: 'Feishu Drive',
      lark_drive: 'Lark Drive',
      notion: 'Notion',
      confluence: 'Confluence',
      yuque: 'Yuque (Юйцюэ)',
      dingtalk: 'Документы DingTalk',
      rss: 'RSS / Atom лента',
      ima: 'Tencent IMA',
      gitlab: 'GitLab',
      nextcloud: 'Nextcloud',
      seafile: 'Seafile'
    },
    logDetail: {
      startTime: 'Время начала',
      endTime: 'Время окончания',
      failedItems: 'Документы с ошибкой',
      failedItemsMore: 'Ещё {n} документов с ошибкой не показаны',
      docsFailedSummary: 'Не удалось синхронизировать документов: {n}'
    },
    logSummary: {
      total: 'Всего запусков',
      success: 'Успешно',
      failed: 'Ошибки',
      items: 'Элементов синхронизации'
    },
    logMetric: {
      total: 'Всего',
      skipped: 'Пропущено',
      failed: 'ошибок'
    },
    logStatus: {
      running: 'Синхронизация',
      success: 'Успешно',
      partial: 'Частично',
      failed: 'Ошибка',
      canceled: 'Отменено'
    },
    step: {
      selectType: 'Выберите тип',
      credentials: 'Учётные данные',
      resources: 'Ресурсы',
      strategy: 'Стратегия'
    },
    conflict: {
      overwrite: 'Перезаписать',
      skip: 'Пропустить существующие'
    },
    seafile: {
      baseUrl: 'URL Seafile',
      apiToken: 'API-токен',
      apiTokenHint: 'Создайте его в Seafile: «Настройки → Web API токен». Учётной записи достаточно прав на чтение выбранных библиотек; токен не передаётся при скачивании файлов.',
      singleLibraryOnly: 'Один источник данных синхронизирует одну библиотеку. Снимите текущий выбор, прежде чем выбрать другую библиотеку.',
      selectionRequired: 'Выберите хотя бы одну библиотеку, папку или файл'
    },
    nextcloud: {
      baseUrl: 'URL Nextcloud',
      baseUrlHint: 'Укажите адрес установки, например https://nextcloud.example.com/cloud, без /remote.php/dav. Для частной сети используйте существующий SSRF_WHITELIST.',
      username: 'Имя пользователя',
      appPassword: 'Пароль приложения',
      appPasswordHint: 'Создайте пароль в разделе «Личные настройки → Безопасность → Устройства и сеансы». Используйте выданные имя пользователя и пароль приложения.',
      selectionRequired: 'Выберите хотя бы одну папку или файл',
      includeExtensions: 'Включить расширения (необязательно)',
      excludeExtensions: 'Исключить расширения (необязательно)',
      extensionsHint: 'Расширения через запятую, например .pdf, .md. Пустой список включает все поддерживаемые форматы. Исключения имеют приоритет. Изменение фильтров влияет на область сверки удалений.'
    },
    gitlab: {
      baseUrl: 'URL GitLab',
      accessToken: 'Персональный токен доступа',
      projects: 'Проекты GitLab',
      projectsHint: 'Укажите ID проекта или путь в пространстве имён (например group/project), а также при необходимости ветку и каталоги.',
      project: 'Проект',
      projectId: 'ID проекта',
      projectIdPlaceholder: 'Например: 12345 или group/project',
      ref: 'Ветка',
      refPlaceholder: 'Оставьте пустым, чтобы использовать ветку по умолчанию',
      paths: 'Каталоги',
      pathsPlaceholder: 'По одному каталогу в строке; оставьте пустым для синхронизации всего проекта',
      addProject: 'Добавить проект',
      projectRequired: 'Добавьте хотя бы один проект GitLab'
    },
    status: {
      active: 'Подключено',
      paused: 'Приостановлено',
      error: 'Ошибка'
    },
    syncMode: {
      incremental: 'Инкрементная',
      full: 'Полная'
    },
    parseMode: {
      inherit: 'Использовать настройки сервера',
      blocks: 'Блочный разбор (по умолчанию)',
      export: 'Экспорт (docx)'
    }
  },
  mermaid: {
    diagram: 'Диаграмма',
    expand: 'На весь экран',
    zoomIn: 'Увеличить',
    zoomOut: 'Уменьшить',
    reset: 'Сброс',
    download: 'Скачать изображение',
    close: 'Закрыть',
    downloading: 'Загрузка...'
  },
  agentEditor: {
    builtinHint: 'Это встроенный агент. Имя и описание нельзя изменить, но можно настроить параметры конфигурации.',
    fileTypes: {
      label: 'Поддерживаемые типы файлов',
      desc: 'Ограничение выбираемых типов файлов. Пустое поле — все типы поддерживаются.',
      allTypes: 'Все типы',
      pdf: 'PDF-документы',
      word: 'Документы Word (.docx/.doc)',
      textLabel: 'Текст',
      text: 'Текстовые файлы (.txt)',
      markdown: 'Документы Markdown',
      csv: 'Файлы CSV',
      excel: 'Таблицы Excel (.xlsx/.xls)',
      imageLabel: 'Изображения',
      image: 'Изображения (.jpg/.jpeg/.png)'
    },
    fallback: {
      fixed: 'Фиксированный ответ',
      model: 'Генерация моделью'
    },
    faq: {
      title: 'Стратегия приоритета FAQ'
    },
    chatParser: {
      label: 'Политика разбора вложений чата',
      desc: 'Выберите движок разбора по типу файла для вложений чата этого агента.',
      waitTimeoutLabel: 'Тайм-аут ожидания разбора вложений (с)',
      waitTimeoutDesc: 'Сколько ход чата ждёт ещё разбираемые вложения, прежде чем продолжить только с готовыми. Увеличьте для больших/сканированных файлов. 0 использует глобальное значение по умолчанию.'
    },
    audioUpload: {
      label: 'Загрузка аудио',
      desc: 'Позволяет пользователям загружать аудиофайлы в чате. Система автоматически транскрибирует их с помощью ASR-модели.',
      asrModel: 'ASR-модель',
      asrModelDesc: 'Модель распознавания речи. Если не настроена, аудиофайлы передаются как заглушки.',
      asrModelPlaceholder: 'Выберите ASR-модель'
    },
    imageUpload: {
      navLabel: 'Загрузка вложений',
      sectionTitle: 'Загрузка вложений',
      sectionDesc: 'Настройте загрузку и разбор изображений, документов и аудио в чате, а также связанные модели',
      label: 'Загрузка изображений',
      desc: 'Разрешить пользователям загружать изображения в чате для понимания через VLM',
      vlmModel: 'Модель VLM',
      vlmModelDesc: 'Визуально-языковая модель для анализа изображений',
      vlmModelPlaceholder: 'Выберите модель VLM',
      vlmModelRequired: 'Модель VLM обязательна при включённой загрузке изображений',
      imageUnderstandingLabel: 'Понимание изображений / OCR сканов',
      imageUnderstandingDesc: 'Для PDF/PPT, состоящих только из изображений (сканов), запускать OCR через VLM, когда текст не извлекается. Увеличивает время разбора; по умолчанию выключено.',
      ocrMaxPagesLabel: 'Макс. страниц OCR для сканов',
      ocrMaxPagesDesc: 'Максимум страниц скана, отправляемых в VLM для OCR. Больше страниц — полнее охват, но медленнее и дороже. 0 использует глобальное значение по умолчанию.',
      useGlobalDefault: '0 = глобальное значение',
      storageProvider: 'Хранилище изображений',
      storageProviderDesc: 'Хранилище для загруженных изображений. Оставьте пустым для системного значения по умолчанию',
      storageProviderPlaceholder: 'Выберите хранилище',
      storageDefault: 'Системное значение',
      notConfigured: 'Не настроено',
      goStorageSettings: 'Перейти к настройкам хранилища'
    },
    llmCallTimeout: {
      label: 'Таймаут вызова LLM',
      desc: 'Таймаут запроса клиента модели (в секундах). Потоковый ответ с непрерывной выдачей данных может длиться дольше указанного времени.',
      hint: 'Оставьте пустым или 0, чтобы использовать значение по умолчанию (120 секунд)',
      placeholder: 'Введите количество секунд, рекомендуемый диапазон 60-1800'
    },
    mcp: {
      label: 'MCP-сервисы',
      desc: 'Выберите MCP-сервисы, доступные агенту',
      selectLabel: 'Выбор MCP-сервисов',
      selectDesc: 'Выберите MCP-сервисы для включения',
      selectPlaceholder: 'Выберите MCP-сервисы',
      authWaitTimeout: 'Тайм-аут ожидания аутентификации (с)',
      authWaitTimeoutDesc: 'Максимальное время ожидания (в секундах) завершения OAuth-аутентификации при запросе во время диалога; по его истечении запрос пропускается (влияет только на MCP-сервисы с OAuth).',
      authWaitTimeoutPlaceholder: 'Default 600 seconds',
      accessLevel: 'Access level',
      accessLevelDesc: 'Whether tools that change data (MCP tools, Wiki writes) run without asking. Read-only leaves them out; confirm asks you each time. MCP tools marked as requiring approval always ask.',
      unavailableService: 'Недоступный сервис'
    },
    agentType: {
      label: 'Тип агента',
      desc: 'Выбор пресета автоматически заполняет системный промпт, список инструментов и рекомендуемую область баз знаний.',
      defaultNamePattern: 'Мой {label}',
      kbIncompatibleWarn: 'Выбранные базы знаний ({count}) несовместимы с текущим типом. Настройте вручную.',
      kbMismatch: {
        ragQa: 'RAG-поиск отключён',
        wikiQa: 'Wiki отключён',
        hybridRagWiki: 'Поиск не включён',
        dataAnalysis: 'Требуется RAG (не FAQ)',
        quickAnswer: 'Быстрый ответ требует RAG-поиск',
        generic: 'Несовместимо с типом'
      }
    },
    im: {
      title: 'Интеграция IM',
      description: 'Подключите агента к платформам мгновенных сообщений, таким как Feishu, Slack, Telegram, DingTalk, Mattermost, QQBot и Yunzhijia',
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
      addChannel: 'Добавить канал',
      channelsTitle: 'IM-каналы',
      disabled: 'Отключено',
      editChannel: 'Редактировать канал',
      deleteConfirm: 'Вы уверены, что хотите удалить этот канал? Это действие не может быть отменено.',
      channelName: 'Имя канала',
      channelNamePlaceholder: 'Введите имя для легкой идентификации',
      channelNameDefaultHint: 'По умолчанию используется название платформы; можно изменить. Если оставить пустым, при сохранении подставится название платформы',
      platform: 'Платформа',
      mode: 'Режим подключения',
      outputMode: 'Режим вывода',
      outputStream: 'Стриминг',
      outputFull: 'Полное выходное значение',
      callbackUrl: 'URL обратного вызова',
      empty: 'Нет IM-каналов',
      unnamed: 'Неименованный канал',
      docLink: 'Руководство по интеграции',
      wecomConsole: 'Консоль WeCom',
      feishuConsole: 'Платформа Feishu',
      larkConsole: 'Платформа Lark',
      slackConsole: 'Консоль Slack API',
      telegramConsole: 'Telegram BotFather',
      dingtalkConsole: 'Платформа DingTalk',
      dingtalkCardTemplateId: 'ID шаблона карточки (необязательно)',
      dingtalkCardTemplateIdHint: 'Создайте шаблон AI-карточки на open-dev.dingtalk.com/fe/card для потоковой передачи с эффектом печатной машинки',
      mattermostConsole: 'Интеграции Mattermost',
      qqbotConsole: 'QQ Open Platform',
      qqbotAPIBaseURLHint: 'Необязательно. Оставьте пустым, чтобы использовать стандартный production API endpoint.',
      qqbotGatewayURLHint: 'Необязательно. Оставьте пустым, чтобы автоматически получить общий WebSocket gateway.',
      yunzhijiaConsole: 'Yunzhijia Open Platform',
      yunzhijiaRobotDoc: 'Документация робота',
      yunzhijiaImageDoc: 'Платформа разработчика (изображения)',
      yunzhijiaModeHint: 'Поддерживаются Webhook и WebSocket; для режима WebSocket не требуется публичный URL обратного вызова.',
      yunzhijiaSendMsgUrl: 'URL отправки сообщений',
      yunzhijiaSendMsgUrlHint: 'Используется для ответов робота.',
      yunzhijiaSecret: 'Секрет подписи (необязательно)',
      yunzhijiaSecretPlaceholder: 'Секрет подписи HmacSHA1 из настроек робота Yunzhijia',
      yunzhijiaSecretHint: 'Если указано, входящие обратные вызовы будут проверяться с помощью подписи HmacSHA1',
      yunzhijiaAppId: 'App ID (загрузка изображений)',
      yunzhijiaAppIdPlaceholder: 'App ID открытой платформы Yunzhijia',
      yunzhijiaAppSecret: 'App Secret (загрузка изображений)',
      yunzhijiaAppSecretPlaceholder: 'App Secret открытой платформы Yunzhijia',
      yunzhijiaAppCredentialHint: 'Используется для получения appAccessToken и загрузки изображений от пользователей.',
      yunzhijiaTimeout: 'Таймаут HTTP (секунды)',
      yunzhijiaTimeoutHint: 'Таймаут отправки ответов через URL отправки сообщений, по умолчанию 10 секунд',
      yunzhijiaAllowedHostSuffix: 'Допустимый суффикс хоста',
      yunzhijiaAllowedHostSuffixHint: 'Ограничить хост URL отправки сообщений этим суффиксом для безопасности (напр. yunzhijia.com)',
      yunzhijiaSendMsgUrlRequired: 'Укажите URL отправки сообщений из настроек робота Yunzhijia',
      mattermostModeHint: 'Mattermost поддерживает только режим Webhook (исходящий вебхук + токен бота).',
      mattermostPostToMain: 'Ответы в основной ленте канала',
      mattermostPostToMainHint: 'Включено — ответы бота как новые сообщения в канале. Выключено (по умолчанию) — ответы в ветке, в основном окне только «N ответов».',
      modeHint: 'Рекомендуется WebSocket — проще настроить',
      consoleTip: 'для получения учётных данных',
      wecomWSEndpointHint: 'Необязательно. Для приватного развёртывания WeCom укажите пользовательский адрес WebSocket. Оставьте пустым для публичного облака. Для адресов внутренней сети добавьте имя хоста в переменную SSRF_WHITELIST.',
      wecomAPIBaseURLHint: 'Необязательно. Для приватного развёртывания WeCom укажите пользовательский базовый URL API. Оставьте пустым для публичного облака. Для адресов внутренней сети добавьте имя хоста в переменную SSRF_WHITELIST.',
      feishuAPIBaseURLHint: 'Необязательно. Оставьте пустым, если сервер имеет прямой доступ в интернет; если для доступа к Feishu требуется прокси, укажите URL обратного прокси (например, nginx, http://host:port). Для адресов внутренней сети добавьте имя хоста в переменную SSRF_WHITELIST.',
      fileKnowledgeBase: 'База знаний для файлов',
      fileKnowledgeBasePlaceholder: 'Выберите базу знаний (необязательно)',
      fileKnowledgeBaseHint: 'При настройке файлы, отправленные пользователями, автоматически сохраняются в эту базу знаний',
      sessionMode: 'Режим сессии',
      sessionModeUser: 'По пользователю (по умолчанию)',
      sessionModeThread: 'По потоку',
      sessionModeHint: 'Режим пользователя: отдельный диалог для каждого пользователя. /clear для нового диалога. Режим потока: отдельный диалог для каждого потока. Несколько человек могут общаться в одном потоке.',
      replyLanguage: 'Язык ответов',
      replyLanguageDefault: 'Использовать системный язык',
      replyLanguageHint: 'Фиксирует язык ответов агента для этого канала. Если не задан, используется язык развёртывания по умолчанию.',
      wechatScanBind: 'Сканировать QR-код для привязки WeChat',
      wechatScanning: 'Отсканируйте QR-код в WeChat',
      wechatBindSuccess: 'WeChat успешно привязан',
      wechatRebind: 'Перепривязать',
      wechatHint: 'Требуется iOS WeChat 8.0.70+, поддерживаются только сообщения 1:1',
      wechatQRExpired: 'Срок действия QR-кода истёк, получите новый',
      wechatBinding: 'Привязка...',
      sectionChannel: 'Информация о канале',
      sectionConnection: 'Подключение',
      sectionCredentials: 'Учётные данные платформы',
      selectPlatform: 'Выберите платформу',
      selectPlatformDesc: 'Выберите платформу обмена сообщениями для подключения',
      enabled: 'Включить канал',
      stepBasic: 'Основное',
      stepConnection: 'Подключение',
      stepKnowledge: 'Хранение файлов',
      stepCredentials: 'Учётные данные',
      sectionAccess: 'Доступ и вывод',
      sectionSession: 'Сессии',
      sectionCallback: 'URL обратного вызова',
      sectionKnowledge: 'Хранение файлов',
      sectionStatus: 'Статус'
    },
    embed: {
      title: 'Встраивание на веб-страницу'
    },
    tools: {
      thinking: 'Размышление',
      thinkingDesc: 'Динамический инструмент рефлексивного решения проблем',
      todoWrite: 'Планирование',
      todoWriteDesc: 'Создание структурированных исследовательских планов',
      askUser: 'Вопрос пользователю',
      askUserDesc: 'Задаёт пользователю вопрос, когда не хватает данных, и ждёт ответа',
      searchKnowledge: 'Поиск по базе знаний',
      searchKnowledgeDesc: 'Семантический, ключевой или гибридный поиск по фрагментам базы знаний',
      readDocument: 'Чтение документа',
      readDocumentDesc: 'Чтение метаданных и фрагментов документа с постраничной навигацией и поиском внутри документа',
      listDocuments: 'Список документов',
      listDocumentsDesc: 'Постраничный просмотр документов базы знаний',
      queryGraph: 'Запрос графа знаний',
      queryGraphDesc: 'Запрос связей из графа знаний',
      dbQuery: 'Запрос к базе данных',
      dbQueryDesc: 'Запрос информации из базы данных',
      dataAnalysis: 'Анализ данных',
      dataAnalysisDesc: 'Понимание файлов данных и проведение анализа',
      dataSchema: 'Схема данных',
      dataSchemaDesc: 'Получение метаинформации табличных файлов',
      requiresKb: '(требуется настройка базы знаний)',
      requiresRagKb: '(требуется база знаний с включённым векторным/ключевым индексом)',
      requiresWikiKb: '(требуется база знаний с включённой Wiki)',
      wikiSearch: 'Поиск по Wiki',
      wikiSearchDesc: 'Поиск страниц Wiki по ключевым словам / семантике',
      wikiReadPage: 'Читать страницу Wiki',
      wikiReadPageDesc: 'Прочитать полное содержимое указанной Wiki-страницы',
      wikiFlagIssue: 'Отметить проблему в Wiki',
      wikiFlagIssueDesc: 'Отметить фактические ошибки или конфликты слияния',
      wikiWritePage: 'Создать/перезаписать Wiki',
      wikiWritePageDesc: 'Создать новую или полностью перезаписать существующую страницу',
      wikiReplaceText: 'Заменить текст в Wiki',
      wikiReplaceTextDesc: 'Заменить конкретный текст на Wiki-странице',
      wikiRenamePage: 'Переименовать Wiki',
      wikiRenamePageDesc: 'Переименовать страницу Wiki и автоматически обновить перекрёстные ссылки',
      wikiDeletePage: 'Удалить Wiki',
      wikiDeletePageDesc: 'Удалить страницу Wiki и автоматически очистить битые ссылки',
      wikiReadIssue: 'Просмотр проблемы Wiki',
      wikiReadIssueDesc: 'Просмотр деталей конкретной проблемы страницы Wiki',
      wikiUpdateIssue: 'Обновить проблему Wiki',
      wikiUpdateIssueDesc: 'Обновить статус проблемы страницы Wiki',
      webSearch: 'Поиск в сети',
      webFetch: 'Загрузка веб-страницы',
      groupBase: 'Базовые',
      groupRag: 'Поиск в базе знаний (RAG)',
      groupWikiRead: 'Чтение Wiki',
      groupWikiEdit: 'Редактирование Wiki',
      groupWikiIssue: 'Проверка Wiki',
      groupData: 'Анализ данных',
      writeWarning: 'Изменяет содержимое Wiki',
      dangerTag: 'Запись',
      statusNoKb: 'База знаний не подключена',
      kbMetricRag: 'RAG баз',
      kbMetricWiki: 'Wiki баз',
      statusInactive: '{count} отмеченных инструментов не смогут работать при текущей конфигурации',
      searchConversations: 'Поиск по прошлым диалогам',
      searchConversationsDesc: 'Ищет то, что обсуждалось в прежних диалогах этого пользователя',
      groupStored: 'Сохранены, но здесь не предлагаются',
      switchManagedDesc: 'Управляется другими настройками агента, а не этим списком, поэтому отметка здесь его не включает. Снимите отметку, чтобы удалить запись.',
      unrecognizedDesc: 'Этого инструмента нет в текущей версии, агент не может его вызвать. Снимите отметку, чтобы удалить запись.',
      keptUnknownWarning: 'Сохранено. Этих сохранённых инструментов нет в текущей версии; они оставлены, но агент не может их вызвать: {names}',
      droppedWarning: 'Сохранено. Эти инструменты управляются другими настройками агента и удалены из списка инструментов: {names}',
      effectiveLabel: 'Итоговые активные инструменты',
      effectiveDesc: 'Рассчитано на основе текущей конфигурации — это набор инструментов, которые агент сможет вызывать после сохранения',
      effectiveEmpty: 'Нет доступных инструментов — агент перейдёт к простому чату с моделью'
    },
    desc: {
      name: 'Задайте легко узнаваемое имя для агента',
      description: 'Кратко опишите назначение и особенности агента',
      systemPrompt: 'Пользовательский системный промпт для определения поведения и роли агента',
      promptInheritance: 'Неизменённый текст следует обновлениям шаблона; изменённый сохраняется как собственный промпт. В режиме агента здесь задаются роль и порядок работы; права инструментов и выбор источников для запроса управляются отдельно.',
      useCustomSystemPrompt: 'Заменить базовый образ',
      useCustomSystemPromptDesc: 'При включении этот промпт заменяет базовый образ платформы; контракты использования инструментов и цитирования по-прежнему добавляются платформой. При выключении он добавляется как дополнительные инструкции после базового образа.',
      leaveEmptyDefault: '(оставьте пустым для системного значения по умолчанию)',
      contextTemplate: 'Определите формат передачи найденного контента модели',
      model: 'Выберите LLM, используемую агентом',
      temperature: 'Контроль случайности выхода: 0 — наиболее детерминированный, 1 — наиболее случайный',
      maxTokens: 'Максимум токенов в ответе. «По умолчанию» — 2048. «Своё» сохраняет введённое число.',
      maxTokensAgent: 'Максимум токенов за один раунд рассуждения, включая JSON вызовов инструментов. По умолчанию — 24576. Пользовательское значение сохраняется как введено.',
      thinking: 'Включить расширенное мышление модели (требуется поддержка модели)',
      queryUnderstandModel: 'Модель для понимания запроса (перефразирование и распознавание намерения). Пустое значение — использовать основную модель чата.',
      rewriteSystemPrompt: 'Системный промпт для перефразирования вопросов (пустое = по умолчанию)',
      rewriteUserPrompt: 'Шаблон пользовательского промпта для перефразирования (пустое = по умолчанию)',
      selectTools: 'Выберите инструменты, доступные агенту',
      maxIterations: 'Ограничивает число вызовов модели основным агентом за один ход.',
      kbScope: 'Выберите область баз знаний, доступных агенту',
      fallbackStrategy: 'Действие при отсутствии релевантного контента в базе знаний',
      fallbackResponse: 'Фиксированный текст при невозможности ответить',
      fallbackPrompt: 'Промпт для генерации ответа модели, когда ответ не найден в базе знаний',
      memoryEnabled: 'Разрешить этому агенту читать и пополнять вашу долговременную память. При выключении разговоры с ним не читают ваши записи и не добавляют новые. Если память выключена в настройках пространства или в личных настройках, включение здесь не подействует'
    },
    selection: {
      all: 'Все',
      selected: 'Выбранные',
      disabled: 'Отключено'
    },
    promptNav: {
      ariaLabel: 'Оглавление промптов',
      system: 'Системный промпт',
      context: 'Шаблон контекста',
      intent: 'Промпты намерений',
      rewriteSystem: 'Перефраз · Система',
      rewriteUser: 'Перефраз · Пользователь',
      fallback: 'Запасной ответ'
    },
    intentPrompts: {
      title: 'Промпты намерений',
      sectionDesc: 'Настройте системные промпты для разных намерений запроса; по умолчанию используются шаблоны системы',
      intentLabel: 'Намерение',
      promptPlaceholder: 'Введите пользовательский системный промпт...',
      customized: 'Настроено',
      empty: 'Нет доступных шаблонов намерений'
    },
    placeholders: {
      available: 'Доступные переменные: ',
      clickToInsert: '(нажмите для вставки)',
      hint: '(нажмите для вставки или введите {\'{{\'} для списка)'
    },
    questionSuggestions: {
      title: 'Рекомендации вопросов в диалоге'
    },
    navGroups: {
      basic: 'Основное',
      knowledge: 'Знания и поиск',
      capability: 'Расширения'
    }
  },
  agentStream: {
    saveToKb: {
      emptyContent: 'Текущий ответ пуст, сохранение в базу знаний невозможно',
      editorOpened: 'Редактор открыт, выберите базу знаний и сохраните'
    },
    copy: {
      emptyContent: 'Текущий ответ пуст, копирование невозможно',
      success: 'Скопировано в буфер обмена',
      failed: 'Ошибка копирования, скопируйте вручную'
    },
    toolStatus: {
      calling: 'Вызов {name}...',
      searchKb: 'Поиск по базе знаний',
      searchKbFailed: 'Ошибка поиска по базе знаний',
      searchMixed: 'Поиск в базе знаний и сети',
      searchMixedFailed: 'Ошибка поиска',
      webSearch: 'Веб-поиск',
      webSearchFailed: 'Ошибка веб-поиска',
      grepSearch: 'Поиск по ключевым словам',
      grepSearchFailed: 'Ошибка поиска по ключевым словам',
      getDocInfo: 'Получение информации о документе',
      getDocInfoFailed: 'Ошибка получения информации о документе',
      viewDocument: 'View document',
      thinkingDone: 'Размышление завершено',
      thinkingFailed: 'Ошибка размышления',
      updateTodos: 'Обновление списка задач',
      updateTodosFailed: 'Ошибка обновления списка задач',
      imageAnalyzing: 'Анализ изображения...',
      imageAnalysisDone: 'Анализ изображения завершён',
      imageAnalysisFailed: 'Ошибка анализа изображения',
      attachmentParsing: 'Разбор вложений...',
      attachmentParsingDone: 'Вложения разобраны',
      attachmentParsingFailed: 'Ошибка разбора вложений',
      queryUnderstanding: 'Анализ запроса...',
      queryUnderstandDone: 'Запрос понят',
      called: 'Вызван {name}',
      calledFailed: 'Ошибка вызова {name}',
      shellExecRunning: 'Выполнение команды в песочнице...'
    },
    mcp: {
      discoverTools: 'Поиск инструментов MCP',
      listServers: 'Сервисы MCP',
      listTools: 'Инструменты MCP',
      searchTools: 'Поиск инструментов MCP',
      describeTool: 'Чтение определения инструмента',
      callTool: 'Вызов инструмента MCP',
      showing: 'Показано {count} из {total}',
      moreAvailable: 'Есть другие результаты',
      empty: 'Нечего показать',
      parameters: 'Параметры',
      expand: 'Показать описание',
      collapse: 'Свернуть',
      required: 'Обязательно',
      fullSchema: 'Полное описание параметров',
      failed: 'Ошибка операции MCP',
      result: 'Результат'
    },
    ragPipeline: {
      searching: 'Поиск в базе знаний...',
      searchingWithQuery: 'Поиск в базе знаний: «{query}»',
      searchingWeb: 'Поиск в сети...',
      searchingWebWithQuery: 'Поиск в сети: «{query}»',
      searchingMixed: 'Поиск в базе знаний и сети...',
      searchingMixedWithQuery: 'Поиск в базе знаний и сети: «{query}»',
      searchDone: 'Поиск завершён'
    },
    attachmentParsing: {
      parsedSummary: 'Разобрано вложений: {count}',
      parsedWithSkipped: 'Разобрано вложений: {parsed}, пропущено (ещё обрабатываются): {skipped}',
      noneReady: 'Нет готовых разобранных вложений'
    },
    knowledgeChunksList: {
      chunkRange: 'Загружено {fetched} / {total} фрагментов',
      page: 'Стр. {page}, по {pageSize} на странице',
      offsetRange: 'Фрагменты {from}–{to}',
      queryMatches: 'Поиск «{query}» в документе: совпадений {count}',
      queryNoMatch: 'Поиск «{query}» в документе: совпадений нет'
    },
    grepResults: {
      chunkHits: '{count} фрагм.',
      keywordHits: '{count} вх.',
      titleMatch: 'заголовок',
      faqEntry: 'FAQ entry'
    },
    search: {
      noResults: 'Совпадения не найдены',
      candidatesBelowThreshold: 'Найдено кандидатов: {count}, ни один не подошёл по релевантности',
      foundResultsFromFiles: 'Найдено {count} результат(ов) из {files} файл(ов)',
      foundResults: 'Найдено {count} результат(ов)',
      foundMixedResults: 'Найдено {count} результат(ов) ({docCount} док., {webCount} веб)',
      webResults: 'Найдено {count} веб-результат(ов)',
      grepSummary: 'Найдено фрагментов: {chunks}, в документах: {docs}'
    },
    plan: {
      inProgress: 'В процессе',
      pending: 'Ожидание',
      completed: 'Завершено'
    },
    toolSummary: {
      getDocument: 'Получить документ: {title}',
      document: 'Документ',
      listChunks: 'Просмотр {title}',
      listFaqEntry: 'View FAQ: {question}',
      deepThinking: 'Глубокое размышление'
    },
    entityLink: {
      kb: 'База знаний',
      doc: 'Документ',
      chunk: 'Фрагмент'
    },
    citation: {
      notFound: 'Содержимое не найдено',
      loadFailed: 'Ошибка загрузки',
      noKbForWiki: 'Не удалось определить связанную базу знаний, Wiki не может быть открыта'
    },
    weknoraDocs: {
      pages: 'Страниц: {count}',
      hits: 'Совпавших разделов: {count}',
      empty: 'Подходящей документации нет',
      outline: 'Оглавление',
      content: 'Текст',
      truncated: 'Текст продолжается',
      failed: 'Не удалось прочитать страницу',
      openDoc: 'Открыть в документации'
    },
    operations: {
      found: 'Доступно операций: {count}',
      unavailableCount: 'Недоступно: {count}',
      empty: 'Подходящих операций нет',
      unavailableHeading: 'Сейчас недоступно',
      parameters: 'Параметры',
      required: 'Обязательно',
      enum: 'Значения',
      range: 'Диапазон {min}–{max}',
      truncated: 'Результат обрезан',
      emptyResult: 'Данные не вернулись',
      failed: 'Операция не выполнена',
      meta: 'Дополнительно',
      risk: {
        read: 'Чтение',
        probe: 'Проверка',
        write: 'Запись',
        destructive: 'Необратимо'
      },
      names: {
        session: {
          list: 'Получить список диалогов'
        },
        automation: {
          list: 'Список автоматизаций',
          create: 'Создать автоматизацию',
          validate_trigger: 'Проверить расписание',
          get: 'Сведения об автоматизации',
          update: 'Изменить автоматизацию',
          delete: 'Удалить автоматизацию',
          pause: 'Приостановить автоматизацию',
          resume: 'Возобновить автоматизацию',
          run_now: 'Запустить автоматизацию сейчас',
          list_runs: 'История запусков автоматизации'
        },
        skill: {
          list_installed: 'Получить список установленных навыков',
          install: 'Установить навык',
          get_installed: 'Получить сведения об установленном навыке',
          uninstall: 'Удалить навык',
          set_enabled: 'Настроить включение навыка',
          list: 'Получить список доступных для запуска навыков',
          list_catalog: 'Получить список навыков рабочего пространства',
          get_catalog: 'Получить сведения о навыке рабочего пространства',
          install_catalog: 'Установить навык из каталога в песочницы'
        },
        model: {
          list: 'Получить список моделей',
          list_providers: 'Получить список поставщиков моделей',
          get_provider: 'Получить сведения о поставщике моделей',
          get: 'Получить сведения о модели',
          delete: 'Удалить модель',
          update: 'Обновить отображаемые сведения о модели',
          copy: 'Копировать настройки модели'
        },
        message: {
          chat_history_stats: 'Получить статистику истории чатов',
          search: 'Поиск в истории диалогов',
          list: 'Получить историю сообщений'
        },
        mcp_service: {
          list: 'Получить список сервисов MCP',
          create: 'Создать сервис MCP',
          get: 'Получить сведения о сервисе MCP',
          update: 'Обновить сервис MCP',
          delete: 'Удалить сервис MCP',
          test: 'Проверить подключение к сервису MCP',
          list_tools: 'Запросить инструменты MCP с сервера',
          get_metadata: 'Просмотреть синхронизированные инструменты MCP',
          refresh_metadata: 'Синхронизировать каталог инструментов MCP'
        },
        web_search_provider: {
          list: 'Список поисковых сервисов',
          get: 'Сведения о поисковом сервисе',
          list_types: 'Типы поисковых сервисов',
          test: 'Проверить подключение к поиску',
          update: 'Изменить поисковый сервис',
          delete: 'Удалить поисковый сервис'
        },
        system: {
          get_info: 'Версия и сведения о системе'
        },
        workspace: {
          get: 'Информация о текущем пространстве',
          update: 'Изменить профиль текущего пространства',
          list_members: 'Участники текущего пространства'
        },
        system_admin: {
          list_admins: 'Список системных администраторов',
          list_users: 'Список пользователей платформы',
          list_settings: 'Системные настройки',
          get_queues: 'Состояние очередей задач',
          list_tasks: 'Задачи очереди'
        },
        wiki: {
          list_folders: 'Получить список папок Wiki',
          create_folder: 'Создать папку Wiki',
          list_issues: 'Получить список проблем страниц Wiki',
          lint: 'Проверить страницы Wiki',
          move_page: 'Переместить страницу Wiki',
          get_page: 'Получить страницу Wiki',
          rebuild_links: 'Перестроить ссылки Wiki',
          revert: 'Восстановить версию страницы Wiki',
          list_revisions: 'Получить список версий страницы Wiki',
          get_stats: 'Получить статистику Wiki'
        },
        knowledge: {
          list: 'Получить список знаний',
          list_folders: 'Получить список папок знаний',
          rename_folder: 'Переименовать или переместить папку',
          create_manual: 'Создать знание вручную',
          create_from_url: 'Создать знание по ссылке',
          batch_delete: 'Удалить знания пакетом',
          batch_reparse: 'Повторно обработать знания пакетом',
          move_to_folder: 'Переместить знания в папку',
          update_manual: 'Обновить знание, созданное вручную',
          move: 'Переместить знания в другую базу',
          get_move_progress: 'Получить статус перемещения знаний',
          set_tags: 'Задать теги знаний',
          get: 'Получить сведения о знании',
          update: 'Обновить знание',
          delete: 'Удалить знание',
          cancel_parse: 'Отменить обработку знания',
          reparse: 'Повторно обработать знание',
          get_parse_progress: 'Получить статус обработки знания'
        },
        faq: {
          batch_update: 'Изменить статусы и теги FAQ пакетно',
          list_entries: 'Получить список вопросов FAQ',
          delete_entries: 'Удалить вопросы FAQ',
          get_entry: 'Получить сведения о вопросе FAQ',
          update_entry: 'Обновить вопрос FAQ',
          add_similar_questions: 'Добавить похожие вопросы',
          create_entry: 'Создать вопрос FAQ'
        },
        knowledge_base: {
          list_parser_engines: 'Получить доступные движки разбора',
          copy: 'Скопировать содержимое базы знаний',
          duplicate: 'Скопировать настройки базы знаний',
          get_copy_progress: 'Получить ход копирования базы знаний',
          list: 'Получить список баз знаний',
          create: 'Создать базу знаний',
          get: 'Получить сведения о базе знаний',
          delete: 'Удалить базу знаний',
          update: 'Обновить базу знаний',
          list_activity: 'Получить журнал активности базы знаний',
          search: 'Поиск в базе знаний',
          list_move_targets: 'Получить список баз знаний для перемещения',
          generate_profile: 'Создать описание базы знаний',
          list_tags: 'Получить список тегов базы знаний',
          create_tag: 'Создать тег базы знаний',
          update_tag: 'Обновить тег базы знаний',
          delete_tag: 'Удалить тег базы знаний',
          list_shared: 'Получить список общих баз знаний'
        },
        chunk: {
          get: 'Получить сведения о фрагменте',
          update: 'Изменить фрагмент',
          list_revisions: 'Получить историю версий фрагмента',
          revert: 'Восстановить версию фрагмента',
          list: 'Получить список фрагментов знаний'
        },
        artifact: {
          list: 'Получить список сгенерированных файлов'
        },
        agent: {
          list: 'Получить список агентов',
          create: 'Создать агента',
          get: 'Получить сведения об агенте',
          delete: 'Удалить агента',
          update: 'Обновить агента',
          copy: 'Копировать агента'
        },
        data_source: {
          list: 'Получить список источников данных',
          get: 'Получить сведения об источнике данных',
          test: 'Проверить подключение к источнику данных',
          sync: 'Синхронизировать источник данных',
          pause: 'Приостановить синхронизацию источника данных',
          resume: 'Возобновить синхронизацию источника данных',
          list_sync_logs: 'Получить журнал синхронизации источника данных',
          get_sync_log: 'Получить ход синхронизации источника данных',
          list_resources: 'Список ресурсов для синхронизации',
          update_sync: 'Изменить настройки синхронизации'
        }
      }
    },
    shellExec: {
      workDir: 'Каталог',
      exitCode: 'Код выхода',
      stdout: 'Stdout',
      stderr: 'Stderr',
      emptyOutput: 'Нет вывода',
      truncated: 'Вывод обрезан',
      killed: 'Прервано по таймауту',
      binarySuppressed: 'Двоичный вывод опущен. Сохраните файлы в каталог артефактов и скачайте их.'
    },
    sandboxFiles: {
      found: 'Найдено файлов: {count}',
      empty: 'Нет файлов',
      truncated: 'Список обрезан',
      wrote: 'Записано',
      replacements: 'Замен: {count}',
      moreLines: 'ещё {count} строк'
    },
    imageView: {
      summary: 'Просмотрены изображения {numbers} из {total} в «{file}»',
      single: 'Просмотрено изображение «{file}»',
      descriptionsHeading: 'Описания от модели компьютерного зрения',
      imageLabel: 'Изображение #{n}',
      noDescription: 'Не удалось описать',
      remaining: 'Ещё не просмотрено: {count}'
    },
    attachmentTarget: {
      list: 'все вложения',
      file: 'вложение',
      images: 'изображения в {name}',
      imagesUnnamed: 'изображения вложения',
      image: 'изображение {n} в {name}',
      imageUnnamed: 'изображение вложения {n}'
    },
    skillFiles: {
      heading: 'Файлы навыка',
      script: 'скрипт',
      instructions: 'Инструкции навыка'
    },
    openPage: {
      open: 'Открыть',
      retired: 'Недоступно',
      openForm: 'Открыть и заполнить',
      opened: 'Открыто ассистентом',
      back: 'Назад',
      endpoint: 'Подключение к: ',
      draftHint: 'Заполнено ассистентом. Добавьте API-ключ или другие учётные данные, проверьте и сохраните сами.'
    },
    pageEdit: {
      title: 'Заполнено полей: {count}',
      undo: 'Отменить',
      undone: 'Заполнение отменено',
      undoSkipped: 'Оставлено без изменений (изменены или исчезли со страницы): {count}',
      unsaved: 'Ничего ещё не сохранено. Проверьте и сохраните на странице.'
    },
    pageAccess: {
      viewed: 'Просмотрена текущая страница: {location}'
    },
    collaboration: {
      tabs: 'Вкладки задач',
      updates: 'Обновлений: {count}',
      mainConversation: 'Основной чат',
      assignment: 'Задание',
      title: 'Подзадачи',
      unnamed: 'Задача без названия',
      phase: {
        tool_running: 'Использует инструмент',
        tool_succeeded: 'Инструмент завершён',
        tool_failed: 'Ошибка инструмента'
      },
      status: {
        queued: 'В очереди',
        running: 'Выполняется',
        waiting: 'Ожидает вашего ввода',
        succeeded: 'Завершена',
        failed: 'Ошибка',
        interrupted: 'Прервана',
        cancelled: 'Отменена',
        needs_attention: 'Требует внимания',
        cancelling: 'Отменяется',
        unknown: 'Статус неизвестен'
      }
    },
    tools: {
      searchKnowledge: 'Поиск по базе знаний',
      grepChunks: 'Поиск по текстовому шаблону',
      webSearch: 'Веб-поиск',
      webFetch: 'Загрузка веб-страницы',
      getDocumentInfo: 'Получение информации о документе',
      listKnowledgeChunks: 'Список фрагментов знаний',
      getRelatedDocuments: 'Поиск связанных документов',
      getDocumentContent: 'Получение содержимого документа',
      wikiReadSourceDoc: 'Читать исходный документ',
      readDocument: 'Чтение документа',
      listDocuments: 'Список документов',
      todoWrite: 'Управление планами',
      askUser: 'Вопрос пользователю',
      requestSecureForm: 'Запрос учётных данных',
      browserFillSecret: 'Ввод учётных данных',
      knowledgeGraphExtract: 'Извлечение графа знаний',
      thinking: 'Размышление',
      attachmentParsing: 'Разбор вложения',
      imageAnalysis: 'Анализ изображения',
      queryUnderstand: 'Понимание запроса',
      queryKnowledgeGraph: 'Запрос графа знаний',
      readSkill: 'Чтение навыка',
      executeSkillScript: 'Выполнение скрипта навыка',
      listSandboxFiles: 'Список файлов песочницы',
      readFile: 'Чтение файла',
      readSandboxFile: 'Чтение файла песочницы',
      writeSandboxFile: 'Запись файла песочницы',
      editSandboxFile: 'Правка файла песочницы',
      shellExec: 'Выполнение команды в песочнице',
      dataAnalysis: 'Анализ данных',
      dataSchema: 'Структура данных',
      databaseQuery: 'Запрос к базе данных',
      findOperations: 'Поиск операций',
      runOperation: 'Выполнение операции',
      spawn_agent: 'Запустить агента',
      list_agents: 'Список агентов',
      send_message: 'Отправить сообщение',
      followup_task: 'Продолжить задачу',
      interrupt_agent: 'Прервать агента',
      wait_agent: 'Ожидать агента',
      openPage: 'Открыть страницу',
      viewPage: 'Просмотр страницы',
      searchWeKnoraDocs: 'Поиск в документации',
      readWeKnoraDoc: 'Чтение документации',
      readPage: 'Просмотр страницы',
      selectTab: 'Выбор вкладки',
      fillPage: 'Заполнение страницы'
    },
    mcpOAuth: {
      waiting: 'Ожидание авторизации · {target}',
      waitingStatus: 'Ожидание авторизации',
      targetWithTool: '{service} › {tool}',
      dockQuestion: 'Авторизуйте {target}, чтобы продолжить',
      titleWithService: 'OAuth · {service}',
      titleWithTool: 'OAuth · {service} › {tool}',
      desc: 'Авторизация откроет новое окно для входа. После успешной авторизации вызов инструмента продолжится автоматически.',
      authorize: 'Авторизовать',
      skip: 'Пропустить',
      countdownShort: '{seconds} с',
      authorizedTag: 'Авторизовано',
      timedOutTag: 'Время авторизации истекло',
      canceledTag: 'Отменено',
      authorizedToast: 'Авторизация успешна, продолжаем',
      startFailed: 'Не удалось начать авторизацию',
      resumeFailed: 'Не удалось возобновить выполнение, повторите попытку',
      skipFailed: 'Не удалось пропустить, повторите попытку'
    },
    hostReview: {
      denied: 'Автопроверка отклонила: {reason}'
    },
    hostApproval: {
      command: 'Команда',
      grantPath: 'Нужен доступ к',
      accessWrite: 'Чтение и запись',
      accessRead: 'Только чтение',
      firstAttemptRan: 'Команда уже выполнялась и завершилась с ошибкой. После разрешения она будет выполнена целиком ещё раз',
      snippet: 'Подробности блокировки',
      sessionRules: 'Если разрешить для сеанса, такие удаления в этой папке больше не будут запрашиваться (имена файлов могут отличаться)',
      reject: 'Отклонить',
      approveOnce: 'Разрешить один раз',
      approveSession: 'Разрешить в этом сеансе',
      approvedOnce: 'Разрешено один раз',
      approvedSession: 'Разрешено в этом сеансе',
      rejectedTag: 'Отклонено',
      submitted: 'Отправлено',
      submitFailed: 'Не удалось отправить',
      userRejected: 'Отклонено пользователем',
      fileOnly: 'Разрешается только этот файл',
      writeMode: 'Режим',
      writeModeOverwrite: 'Перезапись',
      writeModeAppend: 'Добавление',
      writeModeEdit: 'Правка',
      writeBytes: '{bytes} байт',
      preview: 'Содержимое',
      previewTruncated: 'Показаны первые 64 КБ',
      env: 'Переменные окружения',
      skillName: 'Навык',
      stdin: 'Стандартный ввод',
      script: 'Скрипт, который запускает команда'
    },
    toolApproval: {
      title: 'Подтверждение',
      toolDescription: 'Описание инструмента',
      delegatedTask: 'Делегированная задача',
      waitingStatus: 'Ожидание проверки',
      targetWithTool: '{service} › {tool}',
      dockQuestion: 'Разрешить вызов {target}?',
      operationQuestion: 'Разрешить: {action} «{target}»?',
      operationQuestionNoTarget: 'Разрешить: {action}?',
      operationTarget: '{action}: «{target}»',
      characterCount: '{count} симв.',
      argsLabel: 'Аргументы',
      argsModified: 'Изменено',
      allowInSession: 'Разрешать такие действия до конца беседы',
      countdownShort: '{seconds} с',
      approve: 'Подтвердить и выполнить',
      reject: 'Отклонить',
      approvedTag: 'Подтверждено',
      rejectedTag: 'Отклонено',
      parked: 'Ожидает в фоне — можно ответить позже',
      parkedUntil: 'Ожидает в фоне — ответьте до {time}',
      abandonedTag: 'Отменено',
      canceledTag: 'Отменено',
      invalidJson: 'Некорректный JSON',
      submitted: 'Отправлено',
      submitFailed: 'Ошибка отправки',
      userRejected: 'Отклонено пользователем',
      value: {
        document: 'Документ',
        faq: 'FAQ',
        wiki: 'Wiki',
        on: 'вкл',
        off: 'выкл',
        vector: 'Вектор',
        keyword: 'Ключевые слова',
        graph: 'Граф',
        quickAnswer: 'Быстрый ответ',
        smartReasoning: 'Умное рассуждение',
        indexSep: ', '
      },
      detail: {
        type: 'Тип',
        embeddingModel: 'Модель эмбеддинга',
        summaryModel: 'Модель сводки',
        captionModel: 'Описание изображений',
        speechModel: 'Распознавание речи',
        storage: 'Хранилище',
        indexes: 'Индексы',
        name: 'Название',
        title: 'Заголовок',
        status: 'Статус',
        summary: 'Описание',
        model: 'Модель',
        mode: 'Режим',
        url: 'Ссылка',
        from: 'Откуда',
        to: 'Куда',
        folder: 'Папка',
        page: 'Страница',
        version: 'Версия',
        documents: 'Документы',
        knowledgeBases: 'Базы знаний',
        mcpServices: 'Сервисы MCP',
        skills: 'Навыки',
        webSearch: 'Веб-поиск',
        multiTurn: 'Многоходовой диалог',
        transport: 'Транспорт',
        authentication: 'Аутентификация',
        usageInstructions: 'Инструкции по использованию',
        displayName: 'Отображаемое имя',
        enabled: 'Включено',
        sandbox: 'Песочница',
        sandboxes: 'Песочницы',
        systemPrompt: 'Системный промпт',
        content: 'Содержимое',
        kbScope: 'Охват баз знаний',
        mcpScope: 'Охват MCP',
        skillsScope: 'Охват навыков'
      },
      grantLapsed: {
        changed: 'Прежнее разрешение больше не действует: изменились настройки агента автоматизации, ваша роль или предел доступа.',
        expired: 'Срок прежнего разрешения истёк.',
        idle: 'Прежнее разрешение истекло: им долго не пользовались.'
      }
    },
    promptDock: {
      approvalTitle: 'Требуется ваша проверка',
      oauthTitle: 'Требуется авторизация',
      secureFormTitle: 'Нужны ваши учётные данные',
      waiting: 'Ожидает вашего ответа',
      handle: 'Ответить',
      pager: '{current} / {total}',
      previous: 'Назад',
      next: 'Далее',
      collapse: 'Свернуть',
      expand: 'Развернуть'
    },
    secureForm: {
      onlyFillInto: 'Будет введено только на: {domains}',
      observedAt: 'Браузер открыт на: {origin}',
      originUnknown: 'Не удалось определить страницу в браузере. Убедитесь, что открыт сайт, на который вы входите',
      originMismatch: 'Браузер открыт на {origin}, а не на сайте для входа. Проверьте перед вводом',
      originInsecure: 'Страница в браузере не использует HTTPS, учётные данные не будут введены',
      savedAccount: 'Сохранённая учётная запись',
      useNew: 'Ввести новые логин и пароль',
      username: 'Логин',
      password: 'Пароль',
      saveToVault: 'Сохранить в хранилище',
      useOnce: 'Использовать один раз',
      fill: 'Ввести',
      decline: 'Отклонить',
      submittedHidden: 'Отправлено (содержимое скрыто)',
      declined: 'Отклонено',
      timedOut: 'Время истекло',
      canceled: 'Отменено',
      submitFailed: 'Не удалось отправить',
      savedButClosed: 'Учётные данные сохранены в хранилище, но этот запрос уже завершён'
    },
    askUser: {
      answerLabel: 'Ваш ответ',
      title: 'Вопрос к вам',
      selectPlaceholder: 'Выберите',
      textPlaceholder: 'Введите ответ',
      otherPlaceholder: 'Другое (необязательно)',
      decline: 'Не отвечать',
      submit: 'Отправить',
      declinedTag: 'Отказ от ответа',
      submitted: 'Отправлено',
      answeredTag: 'Ответ дан',
      timedOutTag: 'Нет ответа вовремя',
      canceledTag: 'Отменено',
      unansweredTag: 'Без ответа',
      submitFailed: 'Не удалось отправить'
    }
  },
  kbSettings: {
    parser: {
      title: 'Парсер',
      description: 'Выберите парсеры для разных типов файлов. Для ненастроенных типов будет использован встроенный парсер.',
      loading: 'Загрузка...',
      noEngineAvailable: 'Нет доступных парсеров или сервис парсинга не настроен.',
      default: 'По умолчанию',
      goConfig: 'Перейти к настройке →',
      noEngine: 'Нет доступных парсеров',
      fileTypePdf: 'Документы PDF',
      fileTypeWord: 'Документы Word',
      fileTypePpt: 'Презентации',
      fileTypeExcel: 'Таблицы Excel',
      xlsxFirstRowAsHeader: 'Использовать первую строку как контекст столбцов',
      fileTypeEbook: 'Электронные книги',
      fileTypeWebArchive: 'Веб-архивы',
      fileTypeCsv: 'Файлы CSV',
      fileTypeText: 'Текстовые файлы',
      fileTypeJson: 'Файлы JSON',
      fileTypeImage: 'Изображения',
      fileTypeAudiovisual: 'Аудио',
      engines: {
        opendataloader: {
          name: 'OpenDataLoader',
          desc: 'Парсер OpenDataLoader PDF (анализ вёрстки; требуются Java 11+ и opendataloader-pdf)'
        },
        markitdown: {
          name: 'MarkItDown',
          desc: 'Конвертер Microsoft MarkItDown (PDF/Office/HTML и др.)'
        },
        paddleocr_vl_cloud: {
          name: 'PaddleOCR-VL Cloud',
          desc: 'PaddleOCR-VL Cloud API'
        },
        paddleocr_vl: {
          name: 'PaddleOCR-VL',
          desc: 'Самостоятельно развёрнутый сервис PaddleOCR-VL'
        },
        mineru_cloud: {
          name: 'MinerU Cloud',
          desc: 'MinerU Cloud API'
        },
        mineru: {
          name: 'MinerU',
          desc: 'Самостоятельно развёрнутый сервис MinerU'
        },
        anydoc: {
          name: 'anydoc',
          desc: 'Разбор офисных документов внутри процесса (внешний сервис не требуется)'
        },
        simple: {
          name: 'Simple',
          desc: 'Простой формат и анализ изображений (внешний сервис не требуется)'
        },
        builtin: {
          name: 'Встроенный',
          desc: 'Встроенный парсер DocReader (docx/pdf/xlsx и другие сложные форматы)'
        }
      }
    },
    storage: {
      title: 'Хранилище',
      selectDescription: 'Выберите конкретный экземпляр хранилища для привязки этой базы знаний.',
      defaultTag: 'По умолчанию',
      instanceLabel: 'Экземпляр хранилища',
      instanceDesc: 'Для одного типа хранилища можно настроить несколько экземпляров с разными endpoint, бакетами или учётными данными.',
      migrateHint: 'В этой базе знаний уже есть файлы; сменить экземпляр можно только через процедуру миграции хранилища.',
      manageInstances: 'Управление экземплярами хранилища',
      localStorage: 'Локальное хранилище',
      loading: 'Загрузка...'
    },
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
    }
  },
  vectorStoreBadge: {
    systemDefault: 'System default',
    sharedFromOrg: 'Shared from another organization',
    unknownStore: 'Unknown store',
    unavailable: 'Unavailable'
  },
  tools: {
    multiKbSearch: 'Кросс-КБ поиск',
    searchKnowledge: 'Поиск по базе знаний',
    readDocument: 'Чтение документа',
    listDocuments: 'Список документов',
    knowledgeSearch: 'Поиск по базе знаний',
    grepChunks: 'Поиск по текстовому шаблону',
    getChunkDetail: 'Получить детали фрагмента',
    listKnowledgeChunks: 'Список фрагментов знаний',
    listKnowledgeBases: 'Список баз знаний',
    getDocumentInfo: 'Получить информацию о документе',
    queryKnowledgeGraph: 'Запрос к графу знаний',
    think: 'Глубокое размышление',
    todoWrite: 'Составить план'
  },
  commandPalette: {
    placeholder: 'Поиск по базам знаний, файлам, диалогам…',
    clearRecent: 'Очистить',
    retrieval: 'Параметры поиска',
    untitledSession: 'Безымянный диалог',
    hotkey: {
      select: 'Навигация',
      enter: 'Открыть',
      cmdNumber: 'Быстрый переход',
      cmdEnter: 'Начать диалог',
      esc: 'Закрыть'
    },
    empty: {
      noResults: 'Совпадений не найдено',
      askAi: 'Спросить ИИ',
      adjustRetrieval: 'Настроить поиск'
    },
    quick: {
      newChat: 'Новый диалог',
      knowledgeBases: 'Открыть базы знаний',
      agents: 'Открыть агенты',
      organizations: 'Открыть общие пространства',
      settings: 'Открыть настройки',
      productTour: 'Обучение',
      assistant: 'Открыть: {name}'
    },
    match: {
      vector: 'Вектор',
      keyword: 'Ключ.'
    },
    group: {
      chunks: 'Файлы базы знаний',
      messages: 'Сообщения',
      kbs: 'Базы знаний',
      agents: 'Агенты',
      sessionsByTitle: 'Диалоги (по названию)',
      commands: 'Команды',
      recent: 'Недавние',
      quickActions: 'Быстрые действия'
    },
    scope: {
      placeholder: 'Поиск в этой базе знаний…',
      remove: 'Убрать область (Backspace)'
    }
  },
  assistant: {
    title: 'Ассистент Xiaozhi',
    newConversation: 'Новый диалог',
    history: 'История диалогов',
    untitledConversation: 'Диалог без названия',
    historyEmpty: 'Диалогов пока нет',
    historyFailed: 'Не удалось загрузить историю диалогов',
    loadMore: 'Загрузить ещё',
    resize: 'Изменить ширину ассистента',
    welcomeTitle: 'Чем помочь?',
    agentWelcomeDesc: 'Проверьте настройки этого агента, смените модель или узнайте, в каких базах знаний он может искать.',
    welcomeDesc: 'Помогу разобраться в Xiaozhi, упорядочить знания и документы, настроить агентов, инструменты и автоматизации.',
    startFailed: 'Не удалось запустить ассистента. Попробуйте ещё раз.',
    chooseAction: 'Выберите действие или опишите свою задачу.',
    askAboutAnswer: 'Спросить {name} об этом ответе',
    starters: {
      agentConfig: 'Что можно улучшить в настройках этого агента?',
      agentModel: 'Какая модель лучше подойдёт этому агенту?',
      agentKnowledge: 'В каких базах знаний он может искать?',
      wikiIssues: 'Что нужно дополнить или проверить на этой странице Wiki?',
      wikiSummary: 'В чём суть этой страницы Wiki?',
      documentSummary: 'Каковы ключевые выводы этого документа?',
      recentActivity: 'Какие документы недавно загрузили или обновили?',
      agents: 'Для каких вопросов подходит каждый из этих агентов?',
      messageSources: 'На чём основан этот ответ?',
      messageCheck: 'Есть ли в этом ответе ошибки?',
      modelCheck: 'Подходят ли настройки этой модели для её текущего применения?',
      modelUsage: 'Какие агенты и базы знаний используют эти модели?',
      mcpTools: 'Какие инструменты даёт этот MCP-сервис?',
      mcpCheck: 'Что ещё нужно настроить для использования этого сервиса?',
      modelSetup: 'Какие модели мне ещё нужно настроить?',
      mcpSetup: 'Как подключить MCP-сервис?',
      releaseHighlights: 'Что изменилось в текущей версии?',
      gettingStarted: 'Что нужно настроить в Xiaozhi в первую очередь?',
      workflow: 'Как использовать вместе базы знаний, агентов и автоматизации?',
      knowledgeOverview: 'Какую информацию можно найти в каждой из этих баз знаний?',
      knowledgeType: 'Когда лучше использовать документы, FAQ или Wiki?',
      knowledgeOrganize: 'Как организовать мои материалы в удобную базу знаний?',
      knowledgeTopics: 'О чём каждый из этих документов?',
      knowledgeGaps: 'Какие документы не удалось разобрать или их разбор ещё не закончен?',
      faqCoverage: 'На какие частые вопросы отвечают эти FAQ?',
      faqDuplicates: 'Какие FAQ дублируют друг друга и могут быть объединены?',
      faqImprove: 'Какие ответы нужно дополнить или обновить?',
      documentSteps: 'Преврати действия из этого документа в пошаговую инструкцию',
      documentFaq: 'Какие FAQ можно составить из этого документа?',
      wikiSources: 'Какие источники подтверждают выводы этой страницы Wiki?',
      agentCreate: 'Как создать агента, который ищет ответы в базе знаний?',
      agentChoose: 'Какого из этих агентов использовать для поиска по базе знаний?',
      automationIdeas: 'Какие повторяющиеся задачи стоит автоматизировать?',
      automationCreate: 'Настрой еженедельную сводку обновлений базы знаний',
      automationOverview: 'Как в последнее время выполняются мои автоматизации?',
      automationSummary: 'Какой результат дала последняя попытка выполнения этой задачи?',
      automationSchedule: 'Когда эта задача запустится в следующий раз?',
      automationImprove: 'Как улучшить запрос и расписание этой задачи?',
      skillFind: 'Какие из этих навыков стоит добавить агенту?',
      skillAdd: 'Как добавить новый навык и включить его для агента?',
      skillUse: 'Что позволяет делать каждый из добавленных навыков?',
      mcpFind: 'Какие инструменты этих MCP-сервисов может вызывать агент?',
      mcpExamples: 'Как дать агенту доступ к этим MCP-инструментам?',
      mcpUsage: 'Покажи на примере, как пользоваться инструментами этого сервиса',
      modelFit: 'Для каких задач лучше подходит эта модель?',
      modelTypes: 'Как выбрать модели для чата, эмбеддингов и переранжирования?',
      browserConnect: 'Как подключить браузер для работы агента?',
      browserTasks: 'Какие действия на сайтах можно автоматизировать с помощью браузера?',
      browserReconnect: 'Как переподключить браузер, если он показан как не в сети?',
      messageReuse: 'Преврати этот ответ в шаги, которые можно выполнить',
      chatSummary: 'О чём спрашивали в этом разговоре и что в итоге получили?',
      chatCheck: 'Не упустил ли и не ошибся ли последний ответ?',
      chatFollowup: 'Исходя из этого разговора, что ещё можно спросить дальше?',
      artifactRecent: 'Какие файлы были созданы недавно?',
      artifactSources: 'Из какого диалога появился каждый из этих файлов?',
      artifactCreate: 'Как сохранить результат агента в файл?',
      organizationShared: 'Какие базы знаний и агенты есть в каждом общем пространстве?',
      organizationJoin: 'Как вступить в существующее общее пространство?',
      organizationCreate: 'Как создать общее пространство и пригласить участников?'
    },
    context: {
      currentPage: 'Текущая страница',
      detach: 'Не прикладывать текущую страницу',
      attachedTip: 'Приложена текущая страница: {path}',
      detachedTip: 'Нажмите, чтобы приложить текущую страницу: {path}',
      chatMessage: 'Этот ответ',
      pages: {
        knowledge_base: 'База знаний',
        wiki: 'Wiki',
        agent_editor: 'Редактор агента',
        settings_models: 'Модели',
        mcp_services: 'MCP-сервисы',
        settings: 'Настройки',
        chat: 'Чат'
      }
    },
    access: {
      title: 'Уровень доступа',
      capped: 'Не разрешено администратором пространства',
      levels: {
        auto_write: {
          label: 'Автоматически',
          desc: 'Обратимые изменения вносит сразу, перед удалением всё равно спрашивает'
        },
        confirm: {
          label: 'С подтверждением',
          desc: 'Спрашивает перед каждым изменением или удалением'
        },
        read_only: {
          label: 'Только чтение',
          desc: 'Только смотрит, ничего не меняет'
        }
      },
      page: {
        label: 'Просмотр и заполнение страницы',
        desc: 'Читает страницу слева и может заполнять формы. Не нажимает кнопки и не сохраняет.'
      }
    },
    fillNotice: {
      title: 'Ассистент заполнил полей: {count}',
      undo: 'Отменить',
      dismiss: 'Закрыть'
    },
    bubble: {
      label: 'Действия ассистента',
      ask: 'Спросить ассистента',
      polish: 'Улучшить',
      rewrite: 'Переписать',
      translate: 'Перевести',
      continue: 'Продолжить',
      prompts: {
        polish: 'Улучши выделенный текст: исправь опечатки и неудачные формулировки, не меняя смысла, и замени его на месте.',
        rewrite: 'Перепиши выделенный текст яснее и короче и замени его на месте.',
        translate: 'Переведи выделенный текст: китайский на английский, остальные языки на китайский, и замени его на месте.',
        continue: 'Допиши после выделенного текста ещё один абзац, продолжающий мысль.'
      }
    },
    selection: {
      label: 'Выделено',
      lines: 'Выделено строк: {count}',
      detach: 'Не прикладывать выделение',
      tip: 'Выделенный текст будет отправлен с сообщением: {text}',
      tipField: 'Выделенный текст из «{field}» будет отправлен с сообщением: {text}'
    },
    prompts: {
      createAgent: 'Создайте агента по запросу: {request}. Проверьте доступные модели, базы знаний, MCP и навыки, подберите ресурсы. Уточняйте только необходимые данные, соблюдайте текущие права и откройте редактор после создания.',
      createAutomation: 'Создайте задание по расписанию: {request}. Если не указано иное, используйте часовой пояс {timezone}. Подготовьте самостоятельную инструкцию, проверьте расписание и покажите следующие запуски. Не повышайте права исполнения, соблюдайте текущую политику и откройте созданное задание.',
      summarizeActivity: 'Обобщите только loaded_entry_ids этого снимка фильтров: {scope}. Запрашивайте с теми же фильтрами, при необходимости постранично. Укажите ресурсы, исполнителей и результаты. Отличайте события журнала от изменений содержимого; загруженные записи не являются всей историей.',
      explainMcpTools: 'Прочитайте сохранённый каталог инструментов MCP {id}. Объясните возможности и приведите три запроса-примера, отметив устаревшие или неполные данные. Не обновляйте каталог, не вызывайте инструменты и не меняйте настройки.',
      answerToDocument: 'Прочитайте ответ и вопрос: {source}. Подготовьте документ с сохранением ссылок и неопределённостей. Покажите черновик, уточните целевую базу и создайте документ по текущим правилам, не перезаписывая существующие материалы.',
      answerToFaq: 'По ответу и вопросу {source} составьте стандартный вопрос и точный ответ. Покажите черновик, уточните базу FAQ, проверьте похожие записи и сохраните по текущим правилам без перезаписи.',
      answerToAutomation: 'По ответу и вопросу {source} оформите повторяемую работу как самостоятельное задание. Уточните частоту, время и часовой пояс, проверьте и покажите ближайшие запуски, затем создайте по текущим правилам без повышения прав.',
      writePrompt: 'Помоги составить системный промпт с учётом назначения и настроек текущего агента. Если цель неясна, сначала задай вопросы. Вставь предложение в текущий редактор, сохранив переменные шаблона. Не сохраняй и не изменяй сохранённого агента.',
      refinePrompt: 'Улучши приложенный системный промпт: уточни обязанности, требования к ответам и правила использования инструментов. Сохрани исходный смысл и переменные шаблона. Вставь исправления в текущий редактор, не сохраняя и не изменяя сохранённого агента.',
      modelFailure: 'Проанализируй приложенную ошибку подключения с учётом текущих настроек модели и предложи шаги проверки. Не читай и не показывай секретные данные, не изменяй и не сохраняй настройки.',
      mcpFailure: 'Проверьте сервис MCP (ID: {id}) и объясните причину приложенной ошибки получения или синхронизации инструментов. Предложите шаги диагностики без чтения или раскрытия ключей, повторного подключения и изменения настроек.',
      syncFailure: 'Проверьте журнал синхронизации {log} источника «{source}» (ID: {id}). Объясните причину по приложенным примерам ошибок и числу сбоев, предложите дальнейшие действия. Не повторяйте синхронизацию и не изменяйте источник.',
      writeWikiRules: 'Составьте понятные правила для поля «{field}» с учётом назначения текущей базы знаний. Если назначение неясно, сначала спросите меня. Заполните соответствующее поле редактора, сохранив системные правила цитирования и формата вывода. Не сохраняйте и не запускайте повторный разбор.',
      refineWikiRules: 'Уточните приложенные правила поля «{field}», сохранив их смысл. Заполните соответствующее поле редактора, сохранив системные правила цитирования и формата вывода. Не сохраняйте и не запускайте повторный разбор.',
      analyzeChunks: 'Проанализируйте приложенный результат разбиения по отрывкам исходного текста и фрагментов, параметрам этого запуска и статистике. Найдите разрывы смысла, слишком короткие или длинные фрагменты и предложите настройки. Отделите выводы по отрывкам от тех, которым нужен дополнительный исходный текст. Не изменяйте настройки и не перестраивайте базу знаний.'
    },
    actions: {
      summarizeActivity: 'Обобщить эти обновления ({count})',
      toolExamples: 'Примеры использования',
      answerToDocument: 'Создать документ',
      answerToFaq: 'Сохранить как FAQ',
      answerToAutomation: 'Создать задание по расписанию',
      writePrompt: 'Помочь написать',
      refinePrompt: 'Улучшить промпт',
      diagnose: 'Разобрать ошибку',
      refineRules: 'Улучшить правила',
      analyzeChunks: 'Анализ разбиения'
    },
    create: {
      agentTitle: 'Опишите своего агента',
      agentAction: 'Создать с помощником',
      agentHint: 'Опишите пользователей и задачи. Помощник подберёт ресурсы и создаст агента.',
      agentPlaceholder: 'Например: агент поддержки, который отвечает по базе знаний о продукте, указывает источники и сообщает о недостающих данных.',
      automationTitle: 'Создать задачу с помощником',
      automationHint: 'Опишите, что и когда нужно выполнять. Помощник подготовит задачу автоматизации.',
      automationPlaceholder: 'Например: каждую пятницу в 17:00 подводить итоги обновлений базы знаний о продукте за неделю.',
      requestLabel: 'Описание задачи',
      manual: 'Настроить вручную',
      start: 'Продолжить с помощником'
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
      knowledgeBases: 'Помогу выбрать тип базы знаний, упорядочить материалы и найти подходящие источники для ваших вопросов.',
      knowledgeBase: 'Могу кратко пересказать эти документы, показать недавние обновления и найти файлы, разбор которых ещё не завершён.',
      document: 'Могу выделить главное в документе, составить пошаговую инструкцию или подготовить FAQ по его содержанию.',
      faq: 'Могу проверить полноту FAQ, найти повторяющиеся вопросы и помочь сделать ответы понятнее.',
      wiki: 'Могу обобщить содержание страницы, проверить источники и найти разделы, требующие дополнения или обновления.',
      agents: 'Расскажите о своей задаче. Помогу создать агента с подходящей моделью, базами знаний и инструментами.',
      automation: 'Помогу настроить расписание повторяющихся задач, проверить результаты запусков и изменить план выполнения.',
      skills: 'Расскажите о своей задаче. Помогу найти и добавить навыки, а затем подключить их к подходящему агенту.',
      mcp: 'Помогу найти и подключить сервисы MCP, разобраться в их инструментах и настроить их для агентов.',
      browser: 'Объясню, как подключить браузер, какие задачи можно автоматизировать и какие разрешения нужны.',
      model: 'Помогу подключить модели, сравнить их назначение и проверить настройки для вашей задачи.',
      chat: 'Могу кратко сказать, о чём был этот разговор и что получилось, проверить последний ответ и предложить, что спросить дальше.',
      message: 'Могу проверить источники и ключевые сведения этого ответа и подготовить материал для повторного использования.',
      artifacts: 'Могу разложить эти файлы по времени и типу, найти диалог, из которого каждый появился, и объяснить, как сохранить результат агента в файл.',
      organizations: 'Могу показать, какие базы знаний и агенты доступны в каждом общем пространстве, и как создать пространство, вступить в него или пригласить участников.'
    },
    help: {
      label: 'О помощнике',
      title: 'Что умеет помощник Xiaozhi',
      identity: 'Помощник действует от вашего имени. Он видит и меняет только то, что позволяет ваша роль в этом пространстве.',
      page: 'Открываясь, он берёт текущую страницу: может разобрать её содержимое, настроить агентов и автоматизации или заполнить формы. Кнопки он не нажимает и сам не сохраняет.',
      access: 'Под полем ввода можно сменить доступ: только чтение, подтверждение перед изменениями или автоматическое выполнение обратимых правок. Удаление всегда требует подтверждения, а потолок, заданный администратором, превысить нельзя.'
    },
    layout: {
      dock: 'Закрепить справа',
      float: 'Сделать плавающим'
    }
  },
  preview: {
    loading: 'Загрузка предпросмотра документа...',
    loadFailed: 'Не удалось загрузить предпросмотр документа',
    retry: 'Повторить',
    unsupported: 'Этот тип файла не поддерживает онлайн-просмотр',
    unsupportedHint: 'Скачайте файл и откройте локально',
    zoomIn: 'Увеличить',
    zoomOut: 'Уменьшить',
    fullscreen: 'Полноэкранный режим',
    exitFullscreen: 'Выйти из полноэкранного режима',
    htmlRendered: 'Отображение',
    htmlSource: 'Исходный код',
    audioNotSupported: 'Ваш браузер не поддерживает воспроизведение аудио',
    videoNotSupported: 'Ваш браузер не поддерживает воспроизведение видео'
  },
  organization: {
    owner: 'Creator',
    roleUpdated: 'Role updated',
    roleUpdateFailed: 'Failed to update role',
    createdByMe: 'Created by me',
    joinedByMe: 'Joined',
    share: {
      title: 'Поделиться в общем пространстве',
      selectOrg: 'Выберите общее пространство',
      selectOrgPlaceholder: 'Выберите общее пространство для предоставления доступа',
      permission: 'Permission',
      permissionTip: 'Editable permission allows members to modify knowledge base content, Read-only permission only allows search and Q&A',
      shareSuccess: 'Knowledge base shared',
      shareFailed: 'Failed to share',
      unshareSuccess: 'Share cancelled',
      unshareFailed: 'Failed to cancel share',
      sharedTo: 'Shared to',
      noShares: 'Пока не предоставлен доступ ни в одном общем пространстве',
      searchPlaceholder: 'Поиск общих пространств…',
      loading: 'Loading…',
      emptySearch: 'Не найдено общих пространств по запросу «{q}»',
      addShareDialogTitle: 'Поделиться в общем пространстве',
      unshareAction: 'Remove share',
      sharedFrom: 'From',
      permissionReadonly: 'Read-only',
      permissionEditable: 'Editable',
      columns: {
        space: 'Общее пространство',
        permission: 'Permission',
        sharedAt: 'Shared',
        operations: 'Actions'
      }
    },
    settings: {
      pendingJoinRequestsBadge: 'Pending join requests to review'
    },
    role: {
      admin: 'Admin',
      editor: 'Editor',
      viewer: 'Viewer'
    },
    join: {
      title: 'Присоединиться к общему пространству'
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
  mcpServiceDialog: {
    addTitle: 'Добавить сервис MCP',
    addDesc: 'Подключите внешний сервис MCP, чтобы агенты могли вызывать его инструменты.',
    editTitle: 'Редактировать сервис MCP',
    basicSection: 'Основное',
    connectionSection: 'Подключение',
    enableServiceDesc: 'При выключении сервис не будет вызываться',
    unitSecond: 'с',
    name: 'Название сервиса',
    namePlaceholder: 'Введите название сервиса',
    transportType: 'Тип транспорта',
    serviceUrl: 'URL сервиса',
    serviceUrlPlaceholder: 'https://example.com/mcp',
    enableService: 'Включить сервис',
    authConfig: 'Аутентификация',
    authType: 'Способ аутентификации',
    authTypeNone: 'Нет / Свой заголовок',
    authTypeApiKey: 'API Key / Token',
    authTypeOAuth: 'OAuth 2.0 (авторизация при первом подключении)',
    oauthScopes: 'Области (необязательно, через пробел)',
    oauthClientId: 'Client ID (необязательно)',
    oauthClientIdDesc: 'Клиент, заранее зарегистрированный на сервере авторизации. Оставьте пустым, чтобы зарегистрировать клиента автоматически (динамическая регистрация). При смене Client ID обновите и Client Secret.',
    oauthClientSecret: 'Client Secret (необязательно)',
    oauthAuthorization: 'Статус авторизации',
    oauthAuthorized: 'Авторизовано',
    oauthRefreshable: 'Срок действия токена истёк; он будет автоматически обновлён при следующем использовании',
    oauthUnauthorized: 'Не авторизовано',
    oauthAuthorize: 'Авторизоваться',
    oauthReauthorize: 'Авторизовать повторно',
    oauthRevoke: 'Отозвать авторизацию',
    oauthAuthorizeHint: 'Нажатие «Авторизоваться» сначала сохранит текущую конфигурацию, затем запустит авторизацию (каждый пользователь авторизуется отдельно).',
    apiKeyHeader: 'Имя заголовка',
    apiKeyHeaderDesc: 'По умолчанию X-API-Key. Для Bearer укажите Authorization и впишите "Bearer <token>" в значение ниже; для «сырого» токена используйте Authorization и сам токен.',
    credentialValue: 'Секрет / Токен',
    optional: 'Необязательно',
    advancedConfig: 'Дополнительно',
    timeoutSec: 'Таймаут (с)',
    codeImport: {
      toggle: 'Импорт из кода',
      hint: 'Вставьте стандартную JSON-конфигурацию mcpServers для автозаполнения формы',
      parse: 'Разобрать и заполнить',
      editOverwriteHint: 'Импорт перезапишет текущую форму (сохранённые учётные данные не затрагиваются; нажмите «Сохранить», чтобы применить)',
      toasts: {
        filled: 'Форма заполнена, проверьте и сохраните',
        multipleServers: 'Обнаружено несколько сервисов, импортирован первый: {name}'
      },
      errors: {
        empty: 'Сначала вставьте конфигурацию',
        invalidJson: 'Не удалось разобрать, проверьте формат JSON',
        noServer: 'Конфигурация сервиса MCP не найдена',
        missingUrl: 'В конфигурации отсутствует url',
        stdioUnsupported: 'Конфигурации stdio (command/args) не поддерживаются; используйте удалённую конфигурацию с url'
      }
    },
    customHeaders: {
      label: 'Пользовательские заголовки (необязательно)',
      desc: 'HTTP-заголовки, добавляемые к каждому запросу MCP; обычно используются для аутентификации на корпоративном шлюзе, трассировки и т. п.',
      add: 'Добавить заголовок',
      keyPlaceholder: 'Имя заголовка',
      valuePlaceholder: 'Значение заголовка'
    },
    toasts: {
      updated: 'Сервис MCP обновлён',
      updateFailed: 'Не удалось обновить сервис MCP',
      authorized: 'Авторизация выполнена',
      authorizeFailed: 'Не удалось начать авторизацию',
      revoked: 'Авторизация отозвана',
      revokeFailed: 'Не удалось отозвать авторизацию'
    },
    rules: {
      nameRequired: 'Введите название сервиса',
      transportRequired: 'Выберите тип транспорта',
      urlRequired: 'Введите URL сервиса',
      urlInvalid: 'Введите корректный URL'
    }
  },
  mcpMetadata: {
    searchTools: 'Поиск по имени или описанию инструмента',
    retry: 'Повторить',
    details: 'Подробнее',
    description: 'Описание',
    parameters: 'Параметры',
    required: 'Обязательный',
    fullSchema: 'Полное определение',
    noDescription: 'Описание отсутствует',
    noParameters: 'Определение параметров отсутствует',
    enabled: 'Включён',
    approval: 'Требует подтверждения',
    noTools: 'Инструменты не найдены',
    next: 'Далее',
    policyLoadFailed: 'Не удалось загрузить политики. Повторите загрузку перед изменением.',
    policySaveFailed: 'Не удалось сохранить настройки инструмента',
    tools: 'Список Tools',
    cacheHint: 'Если каталог ещё не сохранён, этот шаг подключается автоматически. Позже MCP вызывается только при обновлении.',
    fetch: 'Загрузить снова',
    fetching: 'Подключение и загрузка Tools…',
    toolCount: 'Инструментов: {count}',
    stale: 'Настройки подключения или авторизации изменились. Обновите каталог перед использованием моделью.',
    notSynced: 'Каталог ещё не синхронизирован. Загрузите полные описания и определения параметров.',
    syncRequired: 'Сначала подключитесь и загрузите Tools. Модель может использовать только синхронизированный каталог.',
    syncedAt: 'Синхронизировано:',
    serverDocumentation: 'Исходная документация сервера',
    noServerDocumentation: 'Ответ initialize этого MCP-сервера не содержит instructions / serverInfo.description (оба поля необязательны). Текст инструментов — в description ниже.',
    policyHint: 'Настройки включения и подтверждения сохраняются сразу и не сбрасываются при обновлении каталога.',
    columnTool: 'Инструмент',
    columnEnabled: 'Вкл.',
    columnApproval: 'Подтв.',
    failed: 'Не удалось загрузить каталог инструментов',
    setupProgress: 'Шаги настройки MCP',
    connection: 'Подключение',
    toolsAndUsage: 'Инструменты и назначение',
    previous: 'Назад',
    usage: 'Назначение сервиса',
    usageHint: 'Модель читает обзор, затем загружает нужные инструменты. Ваш текст сохраняется при обновлении.',
    usageInstructions: 'Инструкции по использованию',
    instructionsPlaceholder: 'Кратко опишите назначение, сценарии использования и основные ограничения.',
    generateUsage: 'Создать с ИИ',
    generateHint: 'Создайте краткие инструкции по синхронизированным включённым инструментам. Отредактируйте и сохраните результат.',
    instructionsRequired: 'Инструкции по использованию обязательны',
    generated: 'Создано. Проверьте и сохраните результат.',
    generateFailed: 'Не удалось создать инструкции. Проверьте синхронизацию инструментов и наличие активной модели чата, затем повторите попытку.'
  },
  ollamaSettings: {
    installed: {
      title: 'Установленные модели',
      desc: 'Список моделей, установленных в Ollama'
    },
    download: {
      title: 'Загрузка моделей'
    },
    address: {
      desc: 'API‑адрес локального сервиса Ollama, определяется автоматически. Чтобы изменить, задайте значение в .env'
    },
    status: {
      desc: 'Автоматическая проверка доступности локального сервиса Ollama. При ошибке адреса или остановке сервиса статус будет «Недоступно».'
    }
  },
  modelSettings: {
    moreActions: 'Другие действия',
    title: 'Настройки моделей',
    copySuffix: ' копия',
    builtinTag: 'Встроенная',
    confirmDelete: 'Удалить модель «{name}»?',
    debug: {
      reasoningEffort: 'Интенсивность размышлений',
      reasoningEffortDesc: 'Отправляет reasoning_effort с уровнями, которые сообщает каталог модели',
      title: 'Тест модели',
      description: 'Запрос с сохранёнными настройками модели. Перед проверкой сохраните изменения.',
      groupModel: 'Выбор модели',
      groupInput: 'Тестовый ввод',
      groupResult: 'Результат',
      modelType: 'Тип модели',
      model: 'Модель',
      modelPlaceholder: 'Выберите модель для теста',
      noModelsForType: 'Нет сохранённых моделей этого типа',
      query: 'Ввод',
      queryPlaceholder: 'Введите текст для отправки модели',
      embeddingInput: 'Текст для векторизации',
      embeddingPlaceholder: 'Введите текст для создания embedding',
      vlmPrompt: 'Промпт для изображения',
      vlmPromptPlaceholder: 'Например: подробно опишите это изображение',
      documents: 'Кандидаты документов',
      documentsPlaceholder: 'Введите один документ на строку',
      documentsHint: 'Каждая непустая строка отправляется в модель ReRank как отдельный документ',
      imageFile: 'Файл изображения',
      similarityMode: 'Сходство',
      similarityQuery: 'Запрос',
      similarityQueryPlaceholder: 'Введите запрос, например: собака бежит по траве',
      similarityCandidates: 'Кандидаты',
      similarityCandidatesPlaceholder: 'По одному тексту-кандидату в строке',
      similarityHint: 'Запрос векторизуется как поисковый запрос, кандидаты — как документы, как при реальном поиске; результаты отсортированы по косинусному сходству по убыванию',
      similarityImage: 'Изображение-кандидат (необязательно)',
      similarityImageCandidate: 'Изображение',
      audioFile: 'Аудиофайл',
      chooseFile: 'Выбрать файл',
      parameters: 'Параметры запроса',
      systemPrompt: 'System Prompt',
      systemPromptPlaceholder: 'Необязательно: системный промпт',
      run: 'Запустить тест',
      copyResult: 'Копировать результат',
      history: 'История',
      runLabel: 'Запуск №{n}',
      success: 'Запрос выполнен',
      failed: 'Запрос не выполнен',
      rawResponse: 'Ответ',
      requestPreview: 'Просмотр запроса',
      requestFailed: 'Не удалось выполнить тест модели',
      metrics: {
        api: 'Протокол',
        thinkingFormat: 'Формат размышлений',
        requestedReasoningEffort: 'Запрошенная интенсивность',
        dimension: 'Размерность вектора',
        resultCount: 'Количество результатов',
        answerChars: 'Символов в ответе',
        reasoningChars: 'Символов рассуждения',
        reasoningReturned: 'Рассуждение возвращено',
        textChars: 'Символов транскрипции',
        segmentCount: 'Количество сегментов'
      }
    },
    usage: {
      title: 'Модель нельзя удалить',
      description: 'Модель «{name}» используется в следующих настройках. Откройте каждую конфигурацию и выберите другую модель, затем повторите удаление.',
      knowledgeBases: 'Базы знаний ({count})',
      agents: 'Агенты ({count})',
      openConfiguration: 'Открыть настройки',
      truncated: 'Показаны первые {shown} из {total}',
      longTermMemory: 'Долговременная память'
    },
    builtinModels: {
      title: 'Встроенные модели',
      description: 'Встроенные модели видны всем пространствам. Конфиденциальная информация скрыта, их нельзя редактировать или удалять.',
      descriptionAdmin: 'Встроенные модели видны всем пространствам. Системные администраторы могут изменять конфигурацию и учетные данные; удаление управляется конфигурацией развертывания.',
      viewGuide: 'Посмотреть руководство по управлению встроенными моделями'
    },
    toasts: {
      nameRequired: 'Название модели не может быть пустым',
      nameTooLong: 'Название модели не может превышать 100 символов',
      displayNameTooLong: 'Отображаемое имя не может превышать 100 символов',
      baseUrlRequired: 'Для удалённых API требуется Base URL',
      baseUrlInvalid: 'Некорректный Base URL, укажите правильный адрес',
      dimensionInvalid: 'Размерность встраивания должна быть 128–4096',
      updated: 'Модель обновлена',
      added: 'Модель добавлена',
      saveFailed: 'Не удалось сохранить модель',
      deleted: 'Модель удалена',
      deleteFailed: 'Не удалось удалить модель',
      builtinCannotEdit: 'Встроенные модели нельзя редактировать',
      linkedModelMissing: 'Модель, на которую сослался ассистент, не найдена; возможно, она удалена',
      builtinCannotDelete: 'Встроенные модели нельзя удалить',
      builtinCannotCopy: 'Встроенные модели нельзя копировать',
      copied: 'Модель скопирована',
      copyFailed: 'Не удалось скопировать модель'
    },
    asr: {
      title: 'ASR модели речи',
      desc: 'Модели распознавания речи для транскрибации аудио (например, OpenAI Whisper)',
      empty: 'Нет ASR моделей'
    },
    vllm: {
      title: 'VLLM модели зрения',
      desc: 'Визуально-языковые модели для мультимодального понимания',
      empty: 'Нет VLLM моделей'
    },
    rerank: {
      title: 'Модели ReRank',
      desc: 'Модели для повторной ранжировки результатов',
      empty: 'Нет моделей ReRank'
    },
    embedding: {
      title: 'Модели встраивания',
      desc: 'Модели для векторизации текста',
      empty: 'Нет моделей встраивания'
    },
    chat: {
      title: 'Модели диалога',
      desc: 'Модели для диалога',
      empty: 'Нет моделей диалога'
    },
    source: {
      remote: 'Удалённая',
      openaiCompatible: 'Совместимо с OpenAI',
      custom: 'Своё'
    },
    actions: {
      addModel: 'Добавить модель',
      debugModel: 'Тест модели'
    },
    typeShort: {
      chat: 'Чат',
      embedding: 'Embedding',
      rerank: 'ReRank',
      vllm: 'Зрение',
      asr: 'Речь'
    }
  },
  mcpSettings: {
    addUsageInstructions: 'Добавить инструкции',
    noUsageInstructions: 'Инструкции пока не добавлены',
    title: 'Сервисы MCP',
    description: 'Управление внешними сервисами MCP (Model Context Protocol) для использования инструментов и ресурсов в режиме Agent',
    enabled: 'Включён',
    disabled: 'Отключён',
    addService: 'Добавить сервис',
    empty: 'Сервисы MCP отсутствуют',
    deleteConfirmBody: 'Удалить сервис MCP «{name}»? Действие необратимо.',
    unnamed: 'Без названия',
    builtin: 'Встроенный',
    toolCount: '{count} инструментов',
    toolsNotSynced: 'Инструменты не синхронизированы',
    toolsStale: 'Нужна повторная синхронизация',
    toasts: {
      loadFailed: 'Не удалось загрузить список MCP сервисов',
      enabled: 'Сервис MCP включён',
      disabled: 'Сервис MCP выключен',
      updateStateFailed: 'Не удалось обновить статус сервиса MCP',
      linkedServiceMissing: 'MCP-сервис, на который сослался ассистент, не найден; возможно, он удалён',
      deleted: 'Сервис MCP удалён',
      deleteFailed: 'Не удалось удалить сервис MCP'
    }
  },
  conversationSettings: {
    maxTokens: {
      desc: 'Maximum number of tokens to generate in the response'
    },
    temperature: {
      desc: 'Controls randomness in outputs. 0 is most deterministic; 1 is most random'
    },
    systemPrompt: {
      desc: 'Системный промпт для обычного режима диалога'
    },
    contextTemplate: {
      desc: 'Шаблон промпта для генерации ответов на основе результатов поиска в обычном режиме'
    },
    rerankModel: {
      desc: 'Model for re-ranking search results (optional)'
    },
    chatModel: {
      desc: 'Large language model used for summarization and abstract generation'
    },
    rewritePrompt: {
      desc: 'System prompt used during query rewrite'
    },
    fallbackPrompt: {
      desc: 'Prompt used when fallback strategy is "model"'
    },
    fallbackResponse: {
      desc: 'Text returned when using the fixed fallback strategy'
    },
    fallbackStrategy: {
      desc: 'How to respond when no relevant documents are found'
    },
    enableQueryExpansion: {
      desc: 'При низкой выдаче обращаться к LLM для генерации дополнительных запросов (дороже и медленнее)'
    },
    enableRewrite: {
      desc: 'Automatically rewrite multi-turn queries for better recall'
    },
    rerankThreshold: {
      desc: 'Minimum score required after re-ranking'
    },
    rerankTopK: {
      desc: 'Documents kept after re-ranking'
    },
    vectorThreshold: {
      desc: 'Minimum similarity for vector retrieval'
    },
    keywordThreshold: {
      desc: 'Minimum score for keyword retrieval'
    },
    embeddingTopK: {
      desc: 'Number of documents kept after vector retrieval'
    },
    maxRounds: {
      desc: 'Number of rounds kept for context and query rewrite'
    },
    models: {
      chatGroupLabel: 'Thinking / Chat Models'
    }
  },
  agentSettings: {
    systemPrompt: {
      desc: 'Настройте системный промпт Agent. Подстановки будут заменены во время выполнения.'
    },
    allowedTools: {
      desc: 'Список инструментов, доступных Agent'
    },
    temperature: {
      desc: 'Контролирует случайность ответа. 0 — детерминированно, 1 — максимально случайно'
    },
    rerankModel: {
      desc: 'Повторная ранжировка результатов поиска и нормализация релевантности'
    },
    thinkingModel: {
      desc: 'LLM для рассуждений и планирования'
    },
    maxIterations: {
      desc: 'Ограничивает число шагов рассуждения за одну задачу. «Без ограничения» — цикл идёт, пока модель не остановится сама или вы не остановите её.'
    },
    modelRecommendation: {
      title: 'Model Recommendation'
    }
  },
  uploadTasks: {
    panelLabel: 'Загрузки',
    titleUploading: 'Загрузка {done} из {total}',
    titleParsing: 'Разбор {done} из {total}',
    titleDone: 'Готово',
    titleDoneWithIssues: 'Готово: {ok}, не завершено: {bad}',
    titleCancelled: 'Загрузка отменена',
    destination: 'Куда: {name}',
    destinationMany: 'Куда: баз знаний — {count}',
    remaining: 'осталось около {time}',
    hintUploading: 'Не закрывайте и не обновляйте страницу до завершения загрузки',
    hintParsing: 'Все файлы загружены. Разбор продолжится в фоне — страницу можно закрыть',
    filterAll: 'Все',
    filterIssues: 'Не завершено',
    phaseWaiting: 'В очереди',
    phaseSaving: 'Сохранение…',
    phasePending: 'Ожидает разбора',
    phaseReady: 'Готово',
    phaseParseFailed: 'Ошибка разбора',
    phaseDuplicate: 'Такой файл уже есть',
    phaseCancelled: 'Отменено',
    cancel: 'Отменить',
    cancelAll: 'Отменить все',
    retry: 'Повторить',
    retryFailed: 'Повторить ({count})',
    open: 'Открыть',
    collapse: 'Свернуть',
    expand: 'Развернуть',
    close: 'Закрыть',
    closeConfirm: 'Закрытие отменит загрузку оставшихся файлов ({count})',
    closeConfirmOk: 'Отменить загрузку',
    closeConfirmKeep: 'Продолжить загрузку',
    legend: {
      ready: 'Доступно для поиска',
      active: 'В работе',
      waiting: 'В очереди',
      failed: 'Ошибка',
      duplicate: 'Уже есть'
    },
    eta: {
      seconds: '{n} с',
      minutes: '{n} мин',
      hours: '{n} ч'
    }
  },
  upload: {
    uploadDocument: 'Загрузить документ',
    uploadFolder: 'Загрузить папку',
    onlineEdit: 'Онлайн редактирование',
    deleteRecord: 'Удалить запись'
  },
  time: {
    today: 'Сегодня',
    yesterday: 'Вчера',
    last7Days: 'Последние 7 дней',
    last30Days: 'Последние 30 дней',
    lastYear: 'Последний год',
    earlier: 'Ранее',
    pinned: 'Закреплено'
  },
  platform: {
    multimodalParsing: 'Мультимодальный анализ документов',
    hybridSearchEngine: 'Гибридный поиск + граф знаний',
    ragQandA: 'Вопрос-ответ с ReAct агентом',
    independentTenant: 'Независимое рабочее пространство',
    fullApiAccess: 'Полный доступ к API',
    knowledgeBaseManagement: 'Управление базой знаний',
    loginShowcase: {
      carouselLabel: 'Иллюстрация возможностей базы знаний Renwoxing',
      switchLabel: 'Переключить тему',
      pause: 'Приостановить слайды и анимацию потока',
      play: 'Воспроизвести слайды и анимацию потока',
      reducedMotion: 'Автовоспроизведение отключено для уменьшения движения',
      labels: {
        query: 'Вопрос',
        sourceHit: 'Источник',
        citedAnswer: 'Ссылка',
        sourceMaterial: 'Материалы',
        productKnowledge: 'Продукты',
        delivery: 'Внедрение',
        customerService: 'Поддержка',
        documents: 'Документы',
        webContent: 'Веб',
        existingKnowledge: 'Знания',
        knowledgeEntry: 'База знаний',
        materialsReceived: 'Собрано',
        contentChange: 'Изменения',
        knowledgeReview: 'Проверка',
        knowledgeUpdate: 'Обновлено',
        updateConfirmed: 'Обновление принято'
      },
      themes: {
        review: {
          title: 'Обновляйте знания при изменениях',
          description: 'Проверяйте изменения, чтобы знания оставались полезными',
          summary: 'После проверки и подтверждения изменений обновляются соответствующие знания.',
          mobile: 'Изменение → Проверка → Обновление знаний',
          tab: 'Проверка и обновление'
        },
        intake: {
          title: 'Материалы компании в одном месте',
          description: 'Объединяйте документы, веб-страницы и существующие базы знаний',
          summary: 'Документы, веб-страницы и существующие знания объединяются в общей точке доступа.',
          mobile: 'Документы / Веб / Знания → Общий доступ',
          tab: 'Сбор материалов'
        },
        organization: {
          title: 'Разрозненные документы становятся знаниями',
          description: 'Группируйте материалы по темам и связывайте знания',
          summary: 'Материалы распределяются по темам продуктов, внедрения и обслуживания клиентов.',
          mobile: 'Материалы → Продукты / Внедрение / Сервис',
          tab: 'Организация'
        },
        query: {
          title: 'У каждого ответа есть источник',
          description: 'Задавайте вопросы своими словами и находите ответы с источниками',
          summary: 'По вопросу находится исходный материал, затем отображаются ответ и ссылка на источник.',
          mobile: 'Вопрос → Исходный материал → Ответ с источником',
          tab: 'Ответы и источники'
        }
      }
    }
  },
  font: {
    uiFont: 'Шрифт интерфейса',
    uiFontDescription: 'Шрифт для меню, основного текста, кнопок и большинства элементов интерфейса',
    monoFont: 'Шрифт для кода',
    monoFontDescription: 'Используется для блоков кода, команд терминала, API-ключей, путей к файлам и других технических текстов. Все символы одной ширины, чтобы 0 не путался с O, а 1 — с l.',
    selectFont: 'Выбрать шрифт',
    sansPreview: 'Образец Sample Шрифт — Aa Gg Oo 0123',
    monoPreview: 'const msg = \'Hello\'; // 0O1l',
    fontSize: 'Размер шрифта',
    fontSizeDescription: 'Масштабирует весь интерфейс (текст, иконки, отступы) и применяется немедленно',
    size: {
      small: 'Маленький',
      normal: 'Обычный',
      large: 'Крупный'
    },
    mono: {
      system: 'Системный по умолчанию',
      menlo: 'Menlo',
      monaco: 'Monaco',
      consolas: 'Consolas',
      cascadia: 'Cascadia Code',
      'dejavu-mono': 'DejaVu Sans Mono',
      'liberation-mono': 'Liberation Mono',
      monospace: 'Стандартный моноширинный'
    },
    sans: {
      system: 'Системный по умолчанию',
      pingfang: 'PingFang SC',
      georgia: 'Georgia (с засечками)',
      yahei: 'Microsoft YaHei',
      times: 'Times New Roman (с засечками)',
      'noto-cjk': 'Noto Sans CJK',
      'dejavu-serif': 'DejaVu Serif (с засечками)',
      'sans-serif': 'Стандартный без засечек'
    }
  },
  theme: {
    theme: 'Тема',
    themeDescription: 'Выберите тему оформления интерфейса, поддерживается автоматическое переключение в зависимости от системных настроек',
    light: 'Светлая',
    dark: 'Тёмная',
    system: 'Системная',
    selectTheme: 'Выбрать тему'
  },
  general: {
    title: 'Общие настройки',
    personalSettings: 'Личные настройки',
    description: 'Настройка языка, внешнего вида и других базовых параметров',
    close: 'Закрыть настройки'
  },
  language: {
    zhCN: '简体中文',
    zhTW: 'Традиционный китайский',
    enUS: 'English',
    ruRU: 'Русский',
    koKR: '한국어',
    jaJP: '日本語',
    selectLanguage: 'Выбрать язык',
    language: 'Язык',
    languageDescription: 'Выберите язык отображения интерфейса',
    languageSaved: 'Настройки языка сохранены'
  },
  model: {
    modelName: 'Название модели',
    defaultTag: 'По умолчанию',
    addModelInSettings: 'Перейти в общие настройки для добавления моделей',
    loadFailed: 'Не удалось загрузить список моделей',
    selectModelPlaceholder: 'Выберите модель',
    builtinTag: 'Built-in',
    editor: {
      legacyLocalUnavailable: 'Legacy Ollama service management is retired. The saved record is preserved. To use a local model, select API and enter its OpenAI-compatible endpoint.',
      maxOutputTokensLabel: 'Макс. выходных токенов',
      maxOutputTokensPlaceholder: 'Пусто — значение из каталога',
      maxOutputTokensDesc: 'Лимит вывода на один ответ. Оставьте пустым, чтобы использовать значение каталога для этой модели.',
      addTitle: 'Добавить модель',
      editTitle: 'Редактировать модель',
      sectionType: 'Тип модели',
      typeLabel: 'Тип модели',
      sectionSource: 'Источник',
      sectionProvider: 'Настройки провайдера',
      sectionAdvanced: 'Дополнительные параметры',
      sourceLabel: 'Источник модели',
      sourceRemote: 'API',
      baseUrlLabel: 'Base URL',
      displayNameLabel: 'Отображаемое имя (опционально)',
      displayNamePlaceholder: 'например: модель поддержки',
      displayNameDesc: 'Используется только в интерфейсе. Для вызовов по-прежнему используется имя модели выше.',
      baseUrlPlaceholder: 'например: https://api.openai.com/v1',
      baseUrlPlaceholderVllm: 'например: http://localhost:11434/v1',
      baseUrlPlaceholderAsr: 'например: https://api.openai.com/v1',
      apiKeyOptional: 'API Key (опционально)',
      apiKeyPlaceholder: 'Введите API Key',
      customHeadersLabel: 'Пользовательские заголовки запроса (опционально)',
      customHeadersDesc: 'Дополнительные HTTP-заголовки, добавляемые к запросам к удалённому API модели (например, для авторизации корпоративного шлюза или трассировки). Зарезервированные заголовки, такие как Authorization / Content-Type, игнорируются.',
      customHeadersAdd: 'Добавить заголовок',
      customHeadersKeyPlaceholder: 'Имя заголовка',
      customHeadersValuePlaceholder: 'Значение заголовка',
      testing: 'Проверка...',
      testConnection: 'Проверить соединение',
      dimensionLabel: 'Размерность вектора',
      dimensionPlaceholder: 'например: 1536',
      dimensionOverrideLabel: 'Пользовательская выходная размерность',
      dimensionOverrideDesc: 'Включайте только если документация провайдера подтверждает поддержку параметра dimensions.',
      supportsVisionLabel: 'Поддержка визуального / мультимодального ввода',
      supportsVisionDesc: 'Поддерживает ли модель изображения и другой мультимодальный ввод',
      embeddingImageInputLabel: 'Ввод изображений',
      embeddingImageInputDesc: 'Модель встраивает изображения в то же векторное пространство, что и текст. Для моделей из каталога определяется автоматически, для своих моделей укажите вручную',
      contextWindowLabel: 'Контекстное окно',
      contextWindowPlaceholder: 'Введите общее контекстное окно провайдера',
      contextWindowDesc: 'Общее контекстное окно одного запроса. Расширенный spec имеет приоритет; пустое значение без spec остаётся неизвестным. Укажите лимит провайдера. Агент резервирует токены вывода и запас для сжатия.',
      contextWindowUnknown: 'Неизвестно',
      contextWindowTokens: '{count} токенов',
      maxConcurrencyLabel: 'Лимит фоновой параллельности',
      maxConcurrencyPlaceholder: '0 — использовать глобальное значение',
      maxConcurrencyDesc: 'Ограничивает число одновременных фоновых вызовов (индексация/обогащение) к этой модели, общее для модели по всем репликам. 0 или пусто — используется глобальное значение по умолчанию; интерактивный чат не затрагивается.',
      fillModelAndUrl: 'Сначала заполните идентификатор модели и Base URL',
      remoteBaseUrlRequired: 'Для Remote API необходимо указать Base URL',
      unsupportedModelType: 'Неподдерживаемый тип модели',
      saveAndClose: 'Сохранить и закрыть',
      testDraftHint: 'Проверка текущих настроек подключения без предварительного сохранения.',
      testDraftEditHint: 'Проверка текущих настроек подключения с отдельно сохранённым API-ключом.',
      testStale: 'Настройки изменены. Повторите проверку.',
      connectionSuccess: 'Соединение установлено',
      connectionFailed: 'Соединение не установлено',
      connectionConfigError: 'Соединение не установлено, проверьте конфигурацию',
      providerLabel: 'Провайдер',
      providerPlaceholder: 'Выберите провайдера модели',
      providerDocs: 'Документация моделей {provider}',
      validation: {
        extraFieldRequired: 'Заполните {name}',
        modelNameRequired: 'Введите название модели',
        modelNameEmpty: 'Название модели не может быть пустым',
        modelNameMax: 'Название модели не может превышать 100 символов',
        baseUrlRequired: 'Введите Base URL',
        baseUrlEmpty: 'Base URL не может быть пустым',
        baseUrlInvalid: 'Недопустимый Base URL, введите корректный адрес'
      },
      modelNamePlaceholder: {
        remote: 'например: gpt-4, claude-3-opus',
        remoteVllm: 'например: gpt-4-vision-preview',
        remoteAsr: 'например: whisper-1'
      },
      description: {
        chat: 'Настройте языковую модель для диалогов',
        embedding: 'Настройте модель встраивания для текстовой векторизации',
        rerank: 'Настройте модель для повторного ранжирования результатов',
        vllm: 'Настройте визуально-языковую модель для мультимодального понимания',
        asr: 'Настройте модель распознавания речи для транскрибации аудио',
        default: 'Настройте информацию о модели'
      },
      advanced: {
        toggle: 'Дополнительно',
        compat: {
          label: 'Переопределение совместимости протокола (JSON)',
          placeholder: '{\'{\'} "max_tokens_field": "max_tokens" {\'}\'}',
          desc: 'Заполняйте, только если эндпоинт расходится со значениями каталога, и указывайте лишь изменяемые поля. Пусто — без переопределения.',
          docLink: 'Описание полей',
          invalid: 'Некорректный JSON',
          mustBeObject: 'Должен быть JSON-объект'
        },
        legacyThinking: {
          label: 'Формат параметров размышления (устаревший)',
          catalog: 'Следовать каталогу (рекомендуется)',
          none: 'Не отправлять параметры размышления',
          desc: 'У этой модели сохранилась устаревшая настройка thinking_control. Выберите «Следовать каталогу», чтобы решение принимал каталог.'
        },
        remoteModelName: {
          label: 'Имя модели у поставщика',
          placeholder: 'Пусто — совпадает с именем модели',
          desc: 'ID модели, который реально отправляется поставщику, если отличается от имени выше.'
        },
        api: {
          label: 'Переопределение протокола',
          auto: 'Авто (по поставщику / URL)',
          desc: 'Принудительно задать протокол запросов; обычно не требуется.'
        }
      },
      resolved: {
        title: 'Как вызывается модель',
        empty: 'Укажите поставщика и имя модели, чтобы увидеть, как она будет вызвана',
        failed: 'Не удалось определить',
        protocol: 'Протокол запроса',
        catalog: 'Источник возможностей',
        catalogedYes: 'Встроенный профиль модели',
        catalogedNo: 'Настройки поставщика (модели нет в каталоге)',
        endpoint: 'Адрес запроса',
        thinkingFormat: 'Переключатель размышлений',
        thinkingLevels: 'Доступная интенсивность',
        noThinking: 'Модель не умеет размышлять'
      },
      catalog: {
        reasoning: 'Рассуждение',
        vision: 'Зрение',
        hint: 'Выберите модель из каталога поставщика или введите своё имя модели.'
      }
    }
  },
  error: {
    networkError: 'Ошибка сети, проверьте подключение',
    invalidCredentials: 'Неверное имя пользователя или пароль',
    tokenRefreshFailed: 'Не удалось обновить токен',
    pleaseRelogin: 'Пожалуйста, войдите снова',
    fileSizeExceeded: 'Размер файла не может превышать {size}МБ!',
    unsupportedFileType: 'Неподдерживаемый тип файла!',
    invalidImageLink: 'Invalid image link',
    tokenNotFound: 'Токен входа не найден, войдите снова',
    streamFailed: 'Ошибка потокового соединения',
    initialization: {
      checkFailed: 'Проверка не пройдена',
      testFailed: 'Тест не пройден'
    },
    tenant: {
      listFailed: 'Не удалось получить список пространств',
      searchFailed: 'Не удалось выполнить поиск пространств',
      getApiPrincipalConfigFailed: 'Не удалось получить конфигурацию API principal',
      updateApiPrincipalConfigFailed: 'Не удалось обновить конфигурацию API principal',
      createApiPrincipalTestTokenFailed: 'Не удалось создать тестовый API Token',
      updateFailed: 'Не удалось обновить информацию о пространстве',
      deleteFailed: 'Failed to delete workspace'
    },
    model: {
      createFailed: 'Не удалось создать модель',
      getFailed: 'Не удалось получить модель',
      updateFailed: 'Не удалось обновить модель',
      deleteFailed: 'Не удалось удалить модель'
    },
    auth: {
      loginFailed: 'Ошибка входа',
      registerFailed: 'Ошибка регистрации',
      getUserFailed: 'Не удалось получить информацию о пользователе',
      getTenantFailed: 'Не удалось получить информацию о пространстве',
      updatePreferencesFailed: 'Не удалось обновить настройки',
      refreshTokenFailed: 'Не удалось обновить токен',
      logoutFailed: 'Ошибка выхода',
      validateTokenFailed: 'Ошибка проверки токена'
    }
  },
  mcp: {
    testResult: {
      title: 'Результат теста: {name}'
    }
  },
  system: {
    globalSettings: {
      title: 'Системные настройки',
      audit: {
        action: {
          'system.setting_changed': 'Изменена системная настройка',
          'system.admin_promoted': 'Выдан системный администратор',
          'system.api_key_created': 'Создан платформенный API-ключ',
          'system.api_key_revoked': 'Отозван платформенный API-ключ',
          'system.admin_revoked': 'Отозван системный администратор',
          'system.user_password_reset': 'Сброшен пароль пользователя',
          'system.user_created': 'Создан пользователь',
          'system.queue_task_retried': 'Повторно запущена сбойная задача',
          'system.queue_task_deleted': 'Удалена запись о сбойной задаче',
          'system.queue_task_run_now': 'Задача очереди запущена сейчас',
          'system.queue_task_cancelled': 'Задача очереди отменена',
          'system.queue_archived_purged': 'Очищены все сбойные задачи'
        },
        actorRole: {
          system_admin: 'Системный администратор'
        }
      },
      listConfirm: {
        ssrf: {
          whitelist: {
            remove: {
              header: 'Удалить запись из белого списка SSRF',
              body: 'Удалить {entry} из белого списка SSRF? После удаления запись снова будет блокироваться защитой от SSRF.',
              confirmBtn: 'Удалить'
            },
            add: {
              header: 'Добавить запись в белый список SSRF',
              body: 'Добавить {entry} в белый список SSRF? Соответствующие хосты / IP / подсети будут обходить защиту от SSRF и смогут обращаться к внутренним сервисам через агентов. Добавляйте только полностью доверенные записи.',
              confirmBtn: 'Добавить'
            }
          }
        }
      },
      enumLabels: {
        auth: {
          default_tenant_mode: {
            create_personal: 'Создавать личное пространство',
            tenantless: 'Не создавать пространство'
          },
          registration_mode: {
            self_serve: 'Самостоятельная (любой может зарегистрироваться)',
            invite_register: 'Регистрация по приглашению (нужна действующая ссылка)',
            invite_only: 'Регистрация закрыта (существующие аккаунты могут принять приглашение)'
          }
        }
      },
      keyDescriptions: {
        model: {
          max_concurrency: 'Лимит по умолчанию на количество одновременных фоновых вызовов (индексация/обогащение) к одной модели, привязанный к ID модели и общий для всех реплик. Читается при каждом вызове и применяется сразу без перезапуска. 0 или отрицательное значение отключает лимит по умолчанию (каждая модель всё равно соблюдает собственный лимит, заданный в управлении моделями). Влияет только на фоновые задачи, не на интерактивный чат.'
        },
        asynq: {
          core_concurrency: 'Гарантированный параллелизм разбора документов на процесс; также может использовать общий эластичный пул. Минимум 1; требуется перезапуск.',
          postprocess_concurrency: 'Выделенный параллелизм завершения разбора и запуска обогащения на процесс. Минимум 1; требуется перезапуск.',
          enrichment_concurrency: 'Гарантированный параллелизм сводок, изображений, графа и вопросов на процесс; также может использовать общий пул. Минимум 1; требуется перезапуск.',
          maintenance_concurrency: 'Параллелизм синхронизации, пакетных операций и очистки на процесс, изолированный от пользовательского конвейера. Минимум 1; требуется перезапуск.',
          shared_concurrency: 'Эластичный параллелизм на процесс, общий для разбора и обогащения и используемый стороной с очередью. Минимум 1; требуется перезапуск.',
          wiki_concurrency: 'Параллелизм выделенного пула Wiki на процесс, изолированного от остальных задач. Минимум 1; требуется перезапуск сервиса.'
        },
        tenant: {
          max_owned_per_user: 'Максимальное число пространств, которыми может владеть обычный (не супер) пользователь через самостоятельное создание. Читается при каждом создании пространства и вступает в силу сразу после сохранения. 0 — встроенное значение по умолчанию 10; отрицательное значение полностью снимает ограничение (не рекомендуется для публичных развёртываний).',
          self_service_creation_enabled: 'Разрешает обычным пользователям самостоятельно создавать пространства. Если отключено, они могут только присоединяться по приглашению; межпространственные суперпользователи не ограничены.',
          default_storage_quota_gb: 'Квота хранилища по умолчанию (ГБ) для нового пространства: векторы, оригиналы, текст, индексы и т.д. Читается только при создании — изменения применяются только к новым пространствам и не перезаписывают существующие. 0 или отрицательное значение — встроенное значение по умолчанию 10 ГБ.',
          default_storage_quota_mb: 'Применяется и к личным пространствам, созданным при регистрации. Положительное значение приоритетнее настройки ГБ; ноль и отрицательные значения используют ГБ. Порядок источников каждой настройки: база данных, окружение, значение по умолчанию. Изменения касаются только новых пространств.',
          auto_create_api_key: 'Автоматически создаёт API-ключ full_access и возвращает его открытый токен при создании пространства. Включайте только для старых интеграций; по умолчанию отключено.',
          auto_accept_invitation: 'Если включено, приглашение зарегистрированного пользователя по email сразу добавляет его в пространство без подтверждения во входящих. Если выключено, сохраняется схема «отправка приглашения → подтверждение». Вступает в силу сразу после сохранения.'
        },
        sandbox: {
          docker_enabled: 'Разрешить бэкенд песочницы Docker. Локальный docker.sock равносилен root на хосте, поэтому по умолчанию выключено. Включить может только системный администратор; изменение действует сразу. Включайте только на частной одноузловой установке с примонтированным сокетом демона или удалённым tcp:// с TLS.'
        },
        ssrf: {
          whitelist: 'Белый список SSRF-защиты. Можно указать example.com / *.foo.com / 10.0.0.0/8 / 2001:db8::1. Вступает в силу сразу после сохранения. Переменная окружения SSRF_WHITELIST_EXTRA по-прежнему задаётся при развёртывании и здесь не переопределяется.'
        },
        auth: {
          registration_mode: 'Режим регистрации. Открытая регистрация позволяет любому создать аккаунт; регистрация по приглашению требует действующую ссылку; при закрытой регистрации существующие аккаунты могут принимать приглашения. Изменения применяются сразу.',
          default_tenant_mode: 'Политика пространства после открытой регистрации. create_personal создаёт личное пространство с ролью Owner; tenantless создаёт только аккаунт до принятия приглашения или самостоятельного создания пространства.',
          complex_password_enabled: 'Определяет, требуется ли сложный пароль. При включении пароль должен содержать прописные и строчные буквы, цифры и специальные символы. Изменение вступает в силу немедленно и применяется только к новым пользователям при регистрации, а также при изменении или сбросе пароля. Специальные символы включают: {specialChars}'
        }
      },
      keyLabels: {
        model: {
          max_concurrency: 'Лимит параллелизма модели по умолчанию'
        },
        asynq: {
          core_concurrency: 'Гарантированный параллелизм разбора',
          postprocess_concurrency: 'Параллелизм постобработки',
          enrichment_concurrency: 'Гарантированный параллелизм обогащения',
          maintenance_concurrency: 'Параллелизм обслуживания',
          shared_concurrency: 'Общий эластичный параллелизм',
          wiki_concurrency: 'Параллелизм воркеров Wiki'
        },
        tenant: {
          max_owned_per_user: 'Максимум пространств на пользователя',
          self_service_creation_enabled: 'Разрешить самостоятельное создание пространств',
          default_storage_quota_gb: 'Квота хранилища для новых пространств по умолчанию (ГБ)',
          default_storage_quota_mb: 'Квота хранилища новых пространств (МБ)',
          auto_create_api_key: 'Автоматически создавать API-ключ для новых пространств',
          auto_accept_invitation: 'Автоматически принимать приглашённых зарегистрированных пользователей'
        },
        sandbox: {
          docker_enabled: 'Включить песочницу Docker'
        },
        ssrf: {
          whitelist: 'Белый список SSRF-защиты'
        },
        auth: {
          registration_mode: 'Режим регистрации',
          default_tenant_mode: 'Создание пространства по умолчанию',
          complex_password_enabled: 'Включить сложные пароли'
        }
      },
      runtime: {
        queueDescriptions: {
          default: 'Разбор документов, ручной повторный разбор',
          chat_attachment: 'Разбор вложений, загруженных в сессии',
          postprocess: 'Завершение разбора, запуск обогащения',
          summary: 'Сводки документов и таблиц',
          sync: 'Ручная и плановая синхронизация',
          low: 'Импорт FAQ, пакетный повторный разбор, очистка',
          multimodal: 'OCR изображений, визуальные описания',
          graph: 'Извлечение графа по фрагментам',
          question: 'Генерация вопросов по фрагментам',
          wiki: 'Создание контента, финализация индекса'
        },
        queueNames: {
          default: 'Разбор документов',
          chat_attachment: 'Разбор вложений чата',
          postprocess: 'Постобработка',
          summary: 'Сводки',
          sync: 'Синхронизация источников',
          low: 'Обслуживание и пакеты',
          multimodal: 'Мультимодальные',
          graph: 'Извлечение графа',
          question: 'Вопросы',
          wiki: 'Wiki-конвейер'
        },
        poolDescriptions: {
          core: 'Гарантированная ёмкость разбора документов',
          postprocess: 'Завершение разбора и запуск обогащения',
          enrichment: 'Сводки, изображения, граф и генерация вопросов',
          maintenance: 'Синхронизация источников, пакетные задачи и удаление',
          shared: 'Используется разбором или обогащением по мере очереди',
          wiki: 'Создание содержимого Wiki и финальная обработка'
        },
        pools: {
          core: 'Основной разбор',
          postprocess: 'Оркестрация постобработки',
          enrichment: 'Обогащение',
          maintenance: 'Обслуживание и синхронизация',
          shared: 'Общий эластичный пул',
          wiki: 'Пул Wiki'
        },
        tasks: {
          taskTypes: {
            documentProcess: 'Разбор документа',
            manualProcess: 'Ручная повторная обработка',
            temporaryDocumentProcess: 'Обработка вложения чата',
            postProcess: 'Постобработка документа',
            summary: 'Создание сводки',
            tableSummary: 'Создание сводки таблицы',
            question: 'Генерация вопросов',
            multimodal: 'Обработка изображений',
            graph: 'Извлечение графа знаний',
            sync: 'Синхронизация источника',
            faqImport: 'Импорт FAQ',
            batchReparse: 'Пакетный повторный разбор',
            batchDelete: 'Пакетное удаление',
            move: 'Перемещение документа',
            indexDelete: 'Удаление индекса',
            kbClone: 'Клонирование базы знаний',
            kbDelete: 'Удаление базы знаний',
            wikiIngest: 'Создание Wiki-контента',
            wikiFinalize: 'Завершение Wiki'
          }
        }
      }
    }
  },
  tenant: {
    title: 'Информация о пространстве',
    currentTenant: 'Текущее пространство',
    switchTenant: 'Переключить рабочее пространство',
    statusActive: 'Активен',
    statusInactive: 'Не активирован',
    statusSuspended: 'Приостановлен',
    statusUnknown: 'Неизвестен',
    loadingInfo: 'Загрузка данных...',
    retry: 'Повторить',
    unknown: 'Неизвестно',
    formatError: 'Ошибка формата',
    searchPlaceholder: 'Поиск по имени или введите ID пространства...',
    noMatch: 'Не найдено подходящих пространств',
    switchSuccessTitle: 'Пространство переключено',
    switchSuccessContent: 'Вы вошли в {name}',
    loadTenantsFailed: 'Не удалось загрузить список пространств',
    loading: 'Загрузка...',
    api: {
      title: 'Информация об API',
      userIdLabel: 'ID пользователя',
      userIdDescription: 'Ваш уникальный идентификатор пользователя',
      usernameLabel: 'Имя пользователя',
      usernameDescription: 'Имя, используемое для входа',
      createdAtLabel: 'Время регистрации',
      createdAtDescription: 'Время создания учётной записи'
    },
    messages: {
      fetchFailed: 'Не удалось получить информацию о пространстве',
      networkError: 'Ошибка сети, попробуйте позже'
    },
    deleteDangerZone: {
      title: 'Delete this workspace',
      desc: 'После удаления вы потеряете доступ к личным файлам, чатам и настройкам агентов этого пространства. Аккаунт и общие базы знаний сохранятся.',
      button: 'Delete workspace',
      confirmTitle: 'Delete this workspace?',
      confirmBody: 'Удалить пространство «{name}» без возможности восстановления? Аккаунт и общие базы знаний сохранятся.',
      confirmHint: 'Type the workspace name "{name}" to confirm deletion.',
      confirm: 'Delete workspace',
      nameMismatch: 'Workspace name does not match',
      success: 'Workspace deleted',
      failed: 'Failed to delete workspace'
    },
    leaveDangerZone: {
      title: 'Покинуть это рабочее пространство',
      desc: 'Завершает ваше членство в этом пространстве. Вы потеряете доступ к базам знаний и агентам. Позже вас можно снова пригласить.',
      button: 'Покинуть пространство'
    },
    storage: {
      usageLabel: 'Использование хранения'
    },
    details: {
      idLabel: 'ID пространства',
      nameLabel: 'Название пространства',
      descriptionLabel: 'Описание пространства',
      businessLabel: 'Бизнес пространства',
      statusLabel: 'Статус пространства',
      createdAtLabel: 'Время создания пространства',
      editName: 'Изменить имя',
      editNamePlaceholder: 'Введите новое имя пространства',
      editNameConfirm: 'Сохранить',
      editNameCancel: 'Отмена',
      editNameRequired: 'Имя пространства не может быть пустым',
      editNameSuccess: 'Имя пространства обновлено',
      editNameFailed: 'Не удалось обновить имя пространства',
      editDescription: 'Изменить описание',
      editDescriptionPlaceholder: 'Введите новое описание пространства',
      editDescriptionSuccess: 'Описание пространства обновлено',
      editDescriptionFailed: 'Не удалось обновить описание пространства',
      descriptionEmptyPlaceholder: 'Не указано'
    },
    create: {
      action: 'Создать новое рабочее пространство',
      dialogTitle: 'Создать новое рабочее пространство',
      dialogSubtitle: 'В личном пространстве доступно 10 ГБ для файлов. Базы знаний ContextDB общие для всех аккаунтов.',
      nameLabel: 'Название',
      namePlaceholder: 'Например: Мой новый проект',
      nameRequired: 'Введите название рабочего пространства',
      descriptionLabel: 'Описание (необязательно)',
      descriptionPlaceholder: 'Кратко опишите назначение рабочего пространства',
      submit: 'Создать',
      cancel: 'Отмена',
      success: 'Рабочее пространство создано',
      failed: 'Не удалось создать рабочее пространство',
      disabled: 'В этой системе присоединиться к пространству можно только по приглашению; создать его самостоятельно нельзя.'
    },
    switcher: {
      menuLabel: 'Переключить рабочее пространство',
      currentBadge: 'Текущий',
      homeTooltip: 'Ваше основное рабочее пространство',
      empty: 'Вы состоите только в одном рабочем пространстве'
    }
  },
  chat: {
    suggestedQuestions: 'Вы можете спросить меня',
    refreshSuggestedQuestions: 'Ещё',
    replaceDraftTitle: 'Заменить черновик?',
    replaceDraftBody: 'Заменить текст в поле ввода этим предложенным вопросом.',
    historyLoadFailed: 'Не удалось загрузить историю чата.',
    scrollToLatest: 'Перейти к последнему сообщению',
    thinking: 'Думаю...',
    thinkingAlt: 'Обдумывание...',
    preparingAnswer: 'Подготовка ответа…',
    connectingModelAndGeneratingAnswer: 'Подключение к модели и создание ответа…',
    modelStillResponding: 'Модель отвечает дольше обычного, продолжаем ждать…',
    deepThoughtCompleted: 'Глубокий анализ завершён',
    deepThoughtAlt: 'Глубокий анализ',
    referencesTitle: 'Использовано {count} связанного материала',
    referencesDocCount: 'Использовано {count} документ(ов)',
    referencesWebCount: 'Использовано {count} веб-результат(ов)',
    referencesDocAndWebCount: 'Использовано {docCount} документ(ов) и {webCount} веб-страниц(ы)',
    referencesDrawerTitle: 'Источники',
    referencesDrawerTitleWeb: 'Веб-источники',
    referencesDrawerTitleDocs: 'Документы',
    referencesDrawerTitleTools: 'Результаты инструментов',
    referencesDrawerTitleMixed: 'Источники',
    referencesDrawerWebSection: 'Веб',
    referencesDrawerDocsSection: 'Документы базы знаний',
    referencesDrawerToolsSection: 'Инструменты',
    referencesDrawerEmpty: 'Источники отсутствуют',
    questionMinimapTitle: 'Вопросы',
    questionMinimapPosition: 'Реплика {current} из {total}',
    questionMinimapAriaLabel: 'Содержание вопросов',
    questionMinimapAttachmentPlaceholder: '(Вложение)',
    referenceChunkCount: '{count} фрагмент(ов)',
    fallbackHint: 'В базе знаний не найдено релевантного содержимого. Выше представлен прямой ответ модели.',
    truncatedHint: 'Ответ обрезан на лимите вывода модели за один ответ. Выше — то, что было создано до обрыва.',
    requestInfoTitle: 'Request info',
    requestInfoRequestId: 'Request ID',
    requestInfoMessageId: 'Message ID',
    requestInfoSessionId: 'Session ID',
    requestInfoUrl: 'Request',
    requestInfoSentAt: 'Sent at',
    requestInfoEmpty: 'No request info available',
    channelWeb: 'Веб',
    channelApi: 'API',
    channelIm: 'IM',
    chunkLabel: 'Фрагмент {index}:',
    navigateToDocument: 'Просмотр документа',
    referenceSourceBack: 'Все источники',
    referenceSourceView: 'Открыть оригинал',
    referenceSourceRelocate: 'Найти снова',
    referenceSourceLocating: 'Поиск цитируемого фрагмента…',
    referenceSourceExact: 'Фрагмент источника найден',
    referenceSourcePartial: 'Проверенные фрагменты выделены; часть цитаты не сопоставлена',
    referenceSourceBlock: 'Найдена область источника; точное совпадение текста не подтверждено',
    referenceSourceAmbiguous: 'Найдено несколько совпадений; точное место неизвестно',
    referenceSourceStale: 'Источник или содержимое изменены; точное место цитаты недоступно',
    referenceSourcePrevious: 'Предыдущее место цитирования',
    referenceSourceNext: 'Следующее место цитирования',
    referenceSourceFoundPage: 'Найдено на странице {page}',
    referenceSourceNotFound: 'Не удалось точно найти фрагмент; открыт оригинал',
    referenceSourceOpenWeb: 'Открыть веб-страницу на этом фрагменте',
    chunkIdLabel: 'ID фрагмента:',
    documentIdLabel: 'ID документа:',
    faqIdLabel: 'FAQ ID:',
    faqContainerIdLabel: 'Container ID:',
    faqAnswersLabel: 'Answers:',
    chunkOrdinal: 'Фрагмент {index}',
    previewContent: 'Предпросмотр содержимого',
    noPlanSteps: 'Подробные шаги не предоставлены',
    chunkIndexLabel: 'Фрагмент №{index}',
    chunkPositionLabel: '(позиция: {position})',
    noRelatedChunks: 'Связанные фрагменты не найдены',
    noSearchResults: 'Результаты поиска не найдены',
    relevanceHigh: 'Высокая релевантность',
    relevanceMedium: 'Средняя релевантность',
    relevanceLow: 'Низкая релевантность',
    relevanceWeak: 'Слабая релевантность',
    webSearchNoResults: 'Результаты веб-поиска не найдены',
    otherSource: 'Другие источники',
    webGroupIntro: 'Следующие {count} записей получены из',
    graphConfigTitle: 'Настройки графа',
    entityTypesLabel: 'Типы сущностей:',
    relationTypesLabel: 'Типы связей:',
    graphResultsHeader: 'Найдено {count} связанных результатов',
    graphNoResults: 'Данные графа не найдены',
    unknownLink: 'Неизвестная ссылка',
    contentLengthLabel: 'Длина {value}',
    notProvided: 'Не указано',
    errorMessageLabel: 'Сообщение об ошибке',
    summaryLabel: 'Сводка',
    rawTextLabel: 'Исходный текст',
    collapseRaw: 'Свернуть оригинал',
    expandRaw: 'Развернуть оригинал',
    noWebContent: 'Содержимое страницы не получено',
    webFetchStatusSuccess: 'Fetched',
    webFetchStatusFailed: 'Failed',
    webFetchStatusSkipped: 'Skipped',
    webFetchErrorCode: 'Error code',
    webFetchRetryable: 'Retryable',
    webFetchContentRange: 'Символы {start}–{end} из {total}',
    webFetchPartialContent: 'Часть страницы',
    webFetchSummaryFailed: 'Summary failed',
    lengthChars: '{value} символов',
    lengthThousands: '{value} тыс. символов',
    lengthTenThousands: '{value} ×10⁴ символов',
    noDatabaseRecords: 'Совпадающих записей не найдено',
    nullValuePlaceholder: '<NULL>',
    chunkCountValue: '{count} фрагментов',
    documentDescriptionLabel: 'Описание:',
    documentSourceLabel: 'Источник:',
    documentFileLabel: 'Файл:',
    documentMetadataLabel: 'Метаданные',
    documentInfoEmpty: 'Нет данных о документах',
    positionLabel: 'Позиция:',
    chunkPositionValue: 'Фрагмент №{index}',
    contentLengthLabelSimple: 'Длина содержимого:',
    fullContentLabel: 'Полный текст',
    copyContent: 'Скопировать содержимое',
    knowledgeBaseCount: '{count} баз знаний',
    noKnowledgeBases: 'Нет доступных баз знаний',
    rawOutputLabel: 'Исходный вывод',
    wikiWritePageTitle: 'Запись страницы Wiki',
    wikiReplaceTextTitle: 'Замена текста Wiki',
    wikiRenamePageTitle: 'Переименование страницы Wiki',
    wikiDeletePageTitle: 'Удаление страницы Wiki',
    wikiActionCreated: 'Создано',
    wikiActionUpdated: 'Обновлено',
    wikiActionRenamed: 'Переименовано',
    wikiActionDeleted: 'Удалено',
    wikiFieldSlug: 'Путь страницы',
    wikiFieldTitle: 'Заголовок',
    wikiFieldPageType: 'Тип',
    wikiFieldSummary: 'Резюме',
    wikiFieldOldText: 'Исходный текст',
    wikiFieldNewText: 'Новый текст',
    wikiFieldOldSlug: 'Исходный путь',
    wikiFieldNewSlug: 'Новый путь',
    wikiFieldAffectedPages: 'Затронутые страницы',
    wikiAffectedCount: 'Ссылки на {count} страницах обновлены',
    processError: 'Ошибка обработки',
    sessionExcerpt: 'Выдержка из сессии',
    noAnswerContent: '(Нет содержимого ответа)',
    manualSourcesHeading: 'Источники',
    noMatchFound: 'Совпадений не найдено',
    deleteSessionFailed: 'Ошибка удаления, попробуйте позже!',
    imageTooMany: 'Максимум 5 изображений',
    imageTypeSizeError: 'Поддерживаются только JPG/PNG/GIF/WEBP до 10 МБ',
    imageUploadTooltip: 'Загрузить изображение (вставка/перетаскивание)',
    attachmentUploadTooltip: 'Загрузить вложение (документы, аудио и т.д.)',
    attachmentWithCount: 'Загружено файлов: {count}',
    attachmentTooMany: 'Максимум {max} файлов',
    attachmentTotalTooMany: 'Изображений и вложений вместе не более {max}',
    attachmentTooLarge: 'Файл {name} превышает лимит {max} МБ',
    attachmentTypeNotSupported: 'Неподдерживаемый тип файла: {name}',
    attachmentUploading: 'Загрузка {progress}%',
    attachmentParsing: 'Обработка',
    attachmentReady: 'Готово',
    attachmentUploadFailed: 'Не удалось загрузить вложение',
    attachmentParseFailed: 'Не удалось обработать вложение',
    attachmentStillProcessing: 'Вложение {name} ещё обрабатывается',
    memoryUsedCount: 'Использовано записей памяти: {count}',
    memoryForget: 'Удалить эту запись',
    memoryForgotten: 'Запись удалена',
    memoryForgetFailed: 'Не удалось удалить',
    memoryHint: 'Это записи долговременной памяти, которые видел этот ответ. Удалённая запись больше не используется.',
    backgroundWork: {
      count: '{count} background tasks',
      refresh: 'Refresh',
      structuredResult: 'Structured result',
      updateMessage: 'Additional task instructions',
      sendUpdate: 'Send update',
      stopRequested: 'Cancellation requested',
      actionFailed: 'Action failed. Try again.',
      cancelFailed: 'Cancellation failed. Try again.',
      stop: 'Остановить',
      loading: 'Загрузка вывода…',
      unavailable: 'Вывод недоступен',
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
      tooltip: 'Откатить сюда',
      confirmTitle: 'Откатить сюда?',
      confirmBody: 'Сообщения после этой точки будут удалены. Откат от вопроса также убирает сам вопрос и возвращает его во ввод. Рабочая область откатится, если есть контрольная точка. Отменить действие нельзя.',
      confirmButton: 'Откатить',
      cancelButton: 'Отмена',
      success: 'Сессия откачена',
      reloadFailed: 'Диалог откачен, но историю не удалось перезагрузить. Обновите страницу, если пропали более ранние сообщения',
      failed: 'Не удалось откатить. Попробуйте ещё раз',
      skipped: 'Диалог откачен, рабочая область не изменена',
      skipNoSandbox: 'Диалог откачен, рабочая область не изменена (нет привязанной песочницы)',
      skipNoCheckpoint: 'Диалог откачен, рабочая область не изменена (нет контрольной точки для отката)'
    },
    sandbox: {
      panelTitle: 'Песочница',
      tabArtifacts: 'Файлы',
      tabTerminal: 'Терминал',
      tabDesktop: 'Рабочий стол',
      artifactsEmpty: 'В этом диалоге пока нет созданных файлов',
      artifactScope: 'Область файлов',
      artifactsCurrent: 'Этот ответ',
      artifactsAll: 'Все файлы',
      artifactsSearch: 'Поиск по имени файла',
      artifactsNoMatches: 'Нет подходящих файлов',
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
      paused: 'Песочница этого диалога приостановлена. Запуск терминала возобновит её.',
      stopped: 'Песочница этого диалога не работает: она была остановлена или удалена после долгого простоя. Запуск терминала перезапустит её; если она была удалена, будет создана новая песочница, а прежние файлы и установленные программы не сохранятся.',
      start: 'Запустить терминал',
      connecting: 'Подключение к песочнице…',
      needsProvision: 'В этом диалоге нет работающей песочницы. Создание запустит новую песочницу — она тарифицируется согласно настройкам рабочего пространства.',
      createAndStart: 'Создать и запустить',
      noSandbox: 'Песочницы ещё нет, а у текущего агента не настроен бэкенд песочницы — непонятно, где её создавать. Переключитесь на агента с настроенной песочницей или отправьте сообщение с выполнением кода.',
      unsupported: 'Текущий бэкенд песочницы не поддерживает интерактивный терминал',
      disconnected: 'Соединение потеряно',
      retry: 'Переподключиться',
      sessionEnded: 'Сеанс терминала завершён',
      idleDisconnected: 'Терминал отключён из‑за простоя. Песочница приостановится по своему TTL. Можно подключиться снова.',
      idleDisconnectedNewShell: 'Терминал отключён из‑за простоя, его оболочка завершена (фоновые задачи, запущенные через nohup, продолжают работать). Повторное подключение откроет новую оболочку.',
      disconnectedNewShell: 'Соединение потеряно, оболочка терминала завершена (фоновые задачи, запущенные через nohup, продолжают работать). Повторное подключение откроет новую оболочку.',
      authRevoked: 'Сессия больше не действительна, терминал отключён. Войдите снова и переподключитесь.'
    },
    conversationTime: {
      today: 'Сегодня {time}',
      yesterday: 'Вчера {time}',
      thisYear: '{day}.{month} {time}',
      otherYear: '{day}.{month}.{year} {time}'
    }
  },
  knowledgeEditor: {
    titleCreate: 'Создать базу знаний',
    titleEdit: 'Настройки базы знаний',
    advanced: {
      title: 'Расширенные настройки',
      description: 'Настройте генерацию вопросов и мультимодальные возможности',
      multimodal: {
        label: 'Мультимодальная функция',
        description: 'Включите понимание мультимедийного контента, такого как изображения',
        vllmLabel: 'VLLM модель для зрения',
        vllmDescription: 'Визуально-языковая модель, необходимая для мультимодального понимания',
        vllmPlaceholder: 'Выберите VLLM модель (обязательно)',
        descriptionLanguageLabel: 'Язык описания изображений',
        descriptionLanguageDescription: 'Оставьте пустым, чтобы использовать язык документа',
        descriptionLanguageAuto: 'Следовать языку документа',
        customInstructionsLabel: 'Инструкции обработки изображений',
        customInstructionsDescription: 'Добавьте визуальные приоритеты, сохраняя правила OCR и Markdown',
        customInstructionsPlaceholder: 'Например: распознавать шильдики, модели, коды ошибок и единицы таблиц…',
        imageVectorLabel: 'Поиск по векторам изображений',
        imageVectorDescription: 'Когда включено, после генерации описания изображение также кодируется самой моделью эмбеддингов, и поиск находит изображения по их содержимому, даже если описание этого не упоминает. Нужна модель эмбеддингов с поддержкой изображений; на каждое изображение добавляется один вызов эмбеддинга, а пул кандидатов векторного поиска расширяется. Действует для документов, загруженных или повторно разобранных после включения; страницы сканированных PDF пропускаются',
        imageVectorModelUnsupported: 'Текущая модель эмбеддингов не заявляет поддержку изображений, поэтому векторы изображений не будут ни созданы, ни найдены',
        imageAttrsSchemaLabel: 'Наблюдаемые атрибуты изображений',
        imageAttrsSchemaDescription: 'Модель наблюдает перечисленные ниже атрибуты (определены реестром бэкенда), чтобы управлять политикой OCR',
        imagePipelineSectionLabel: 'Схема разбора изображений',
        imagePipelineSectionDescription: 'Когда включён мультимодальный разбор, можно выбрать способ разбора изображений.',
        imagePipelineLabel: 'Способ разбора',
        advancedSettingsLabel: 'Дополнительные настройки',
        notesLabel: 'Дополнительные пояснения',
        imagePipelinePlaceholder: 'Выберите способ разбора',
        imagePipelineLoading: 'Загрузка пайплайнов…',
        imagePipelineLoadError: 'Не удалось загрузить пайплайны',
        imagePipelineValidateError: 'Текущие настройки не удалось проверить; бэкенд проверит их при сохранении.',
        imageAttrsOcrConditions: 'Запуск OCR по наблюдаемым условиям атрибутов',
        imageAttrsOcrConditionsDesc: 'Когда наблюдаемые атрибуты соответствуют условиям ниже, для изображения выполняется OCR',
        imagePipelineKbNote: 'По умолчанию следуют настройкам базы знаний; можно изменить для этой задачи'
      },
      tableMetadataInstructions: {
        label: 'Инструкции метаданных таблиц',
        description: 'Добавьте бизнес-контекст и семантику полей к сводкам CSV/Excel',
        placeholder: 'Например: таблица заказов продаж, суммы в CNY, status использует внутренние коды…'
      },
      autoTag: {
        label: 'Автоматические теги',
        description: 'После разбора документа выбираются подходящие существующие теги базы знаний. Теги не создаются и не удаляются, но выполняется дополнительный вызов модели.',
        modelLabel: 'Модель классификации',
        modelDescription: 'Если не выбрана, используется модель резюмирования базы знаний.',
        modelPlaceholder: 'Выберите модель классификации',
        maxTagsLabel: 'Максимум тегов на документ',
        maxTagsDescription: 'Автоматически связывать от 1 до 10 существующих тегов.',
        skipIfTaggedLabel: 'Пропускать документы с тегами',
        skipIfTaggedDescription: 'Если включено, документы с тегами, заданными вручную при загрузке, не размечаются автоматически, что сохраняет намерение пользователя.'
      },
      profile: {
        label: 'Автоматическое описание базы знаний',
        description: 'После добавления, удаления или повторного резюмирования документов описание выводится из агрегата профилей документов. Сам агрегат не вызывает модель; один небольшой вызов выполняется только при изменении агрегата.',
        modelLabel: 'Модель генерации',
        modelDescription: 'Если не выбрана, используется модель резюмирования базы знаний.',
        modelPlaceholder: 'Выберите модель генерации',
        instructionsLabel: 'Требования к описанию',
        instructionsDescription: 'Укажите аудиторию, термины, которые нужно сохранить, или стиль; формат вывода остаётся фиксированным.',
        instructionsPlaceholder: 'Например: для сотрудников поддержки, описать продуктовые линейки простыми словами, сохранить номера моделей…'
      },
      questionGeneration: {
        modelLabel: 'Модель генерации вопросов',
        modelDescription: 'Оставьте пустым, чтобы использовать модель сводки базы знаний.',
        modelPlaceholder: 'Выберите модель генерации вопросов',
        label: 'AI генерация вопросов',
        description: 'Генерация связанных вопросов для каждого фрагмента с помощью LLM при парсинге документа для улучшения полноты поиска. Включение увеличит время парсинга документа.',
        countLabel: 'Количество вопросов',
        countDescription: 'Количество вопросов для генерации на фрагмент документа (1-10)',
        instructionsLabel: 'Инструкции генерации вопросов',
        instructionsDescription: 'Задайте аудиторию, сценарий и формулировки, сохраняя стабильный формат вывода',
        instructionsPlaceholder: 'Например: естественные вопросы службы поддержки без экзаменационного стиля…'
      }
    },
    asr: {
      title: 'Распознавание речи для аудио',
      description: 'Настройте ASR (речь → текст). При включении можно загружать аудиофайлы и транскрибировать их в текст (mp3, wav, m4a, flac, ogg и др.). Загрузка видео не поддерживается.',
      label: 'Включить распознавание речи для аудио',
      desc: 'При включении в базу можно загружать аудио; речь транскрибируется в текст для парсинга и поиска',
      modelLabel: 'Модель ASR',
      modelDescription: 'Модель распознавания речи для транскрибации аудио (например, OpenAI Whisper)',
      modelPlaceholder: 'Выберите модель ASR',
      languageLabel: 'Подсказка языка аудио',
      languageDescription: 'Необязательно. Основной язык может улучшить распознавание некоторыми ASR-моделями; пустое значение включает автоопределение.',
      languagePlaceholder: 'Например zh или en; пусто — автоопределение'
    },
    multimodal: {
      title: 'Обработка изображений',
      description: 'Настройте понимание изображений для парсинга и поиска нетекстового контента'
    },
    chunking: {
      title: 'Настройки разбиения',
      description: 'Управляет тем, как загруженные документы разбиваются перед эмбеддингом. Значения по умолчанию подходят для большинства случаев — настройте только если качество поиска плохое.',
      sizeLabel: 'Размер блока',
      sizeDescription: 'Максимальное количество символов в блоке (100–4000). По умолчанию 512 ≈ 100–130 английских токенов. Меньше для FAQ (200–400), больше для повествовательных документов (1000–2000).',
      characters: 'символов',
      overlapLabel: 'Перекрытие блоков',
      overlapDescription: 'Количество символов, общих для соседних блоков (0–500). По умолчанию 80 ≈ 15% размера — оптимум по текущим исследованиям. 0 для FAQ/структурированных данных, 150–200 для длинных повествований.',
      separatorsLabel: 'Разделители',
      separatorsDescription: 'Символы или строки, которые сплиттер предпочитает при резке. Разделители более высокого приоритета пробуются первыми; порядок по умолчанию: абзацы → предложения → пунктуация.',
      separatorsPlaceholder: 'Выберите или настройте разделители',
      parentChildLabel: 'Родительско-дочернее разбиение',
      parentChildDescription: 'Двухуровневое разбиение: маленькие дочерние блоки используются для векторного матчинга (точные совпадения), большой родительский блок возвращается LLM (более богатый контекст). Рекомендуется для длинных документов (>10 страниц); пропустите для коротких FAQ для экономии хранилища.',
      parentChunkSizeLabel: 'Размер родительского блока',
      parentChunkSizeDescription: 'Размер контекстного блока, возвращаемого LLM (512–8192). По умолчанию 4096 ≈ 1000 английских токенов, комфортно вписывается в любое современное контекстное окно.',
      childChunkSizeLabel: 'Размер дочернего блока',
      childChunkSizeDescription: 'Размер встроенного блока для векторного матчинга (64–2048). По умолчанию 384 ≈ 80 токенов — оптимум для эмбеддеров уровня sentence-transformer / BGE.',
      strategyLabel: 'Стратегия разбиения',
      strategyDescription: 'Выберите способ разбиения документов на блоки. Автоматический режим анализирует каждый документ и выбирает оптимальную стратегию.',
      strategyPlaceholder: 'Выберите стратегию разбиения (по длине, если не указано)',
      overlapWarning: 'Перекрытие велико по сравнению с размером блока — блоки будут содержать большую часть одинакового контента.',
      advancedLabel: 'Расширенные параметры',
      tokenLimitLabel: 'Лимит токенов на блок',
      tokenLimitDescription: 'Жёсткий лимит токенов на блок (0–8192). 0 = выкл (только символы). Активируйте, когда у вашего эмбеддера небольшой токен-лимит: 200 для MiniLM (256 ток), 400 для BGE/Cohere (512 ток). Современные эмбеддеры (OpenAI, Voyage, Jina-v3) поддерживают >2000 токенов — оставьте 0.',
      languagesLabel: 'Языковые подсказки',
      languagesDescription: 'Ограничивает эвристические паттерны выбранными языками (DE/EN/ZH). Пусто = автоопределение из образца. Установите явно для однородных корпусов, чтобы избежать ложных срабатываний между языками.',
      languagesPlaceholder: 'Автоопределение',
      debug: {
        toggle: 'Проверить разбиение',
        toggleHint: 'Запустить разбиение для примера текста без повторной загрузки',
        sampleLabel: 'Пример текста',
        samplePlaceholder: 'Вставьте фрагмент Markdown / простого текста, чтобы увидеть, как его разобьет текущая конфигурация…',
        presetLabel: 'Загрузить пример:',
        runButton: 'Запустить предпросмотр',
        loading: 'Запуск разбиения на примере…',
        errorPrefix: 'Ошибка предпросмотра',
        selectedTier: 'Выбранная стратегия',
        rejected: 'Отклоненные уровни',
        contextHeader: 'Контекстный заголовок',
        fallbackWarning: 'Цепочка стратегий полностью исчерпана — текущие настройки не позволяют разумно разбить контент',
        stats: {
          chunks: 'блоков',
          truncated: 'обрезано; всего {total}'
        },
        profile: {
          lines: 'строк',
          chars: 'символов',
          headings: 'заголовков Markdown',
          pageBreaks: 'разрывов страниц',
          chapterMarkers: 'маркеров глав',
          languages: 'языки'
        },
        samples: {
          markdown: 'Markdown-документ',
          faq: 'Список FAQ',
          chapter: 'Главы PDF',
          plain: 'Обычный текст'
        }
      },
      languageOptions: {
        de: 'Немецкий',
        en: 'Английский',
        zh: 'Китайский'
      },
      strategies: {
        legacy: {
          label: 'По длине',
          tooltip: 'Игнорирует структуру и разбивает рекурсивно по числу символов и разделителям — оригинальное поведение. Используйте, если стратегии с учётом структуры работают некорректно.'
        },
        heuristic: {
          label: 'По структуре',
          tooltip: 'Разбивает по обнаруженным структурным признакам: разрывы страниц, нумерованные разделы, многоязычные маркеры глав (DE/EN/ZH), заголовки в верхнем регистре. Идеально для PDF без заголовков Markdown.'
        },
        heading: {
          label: 'По заголовкам',
          tooltip: 'Разбивает по границам заголовков Markdown (#, ##, ###); каждый фрагмент получает свой путь заголовков. Подходит для хорошо структурированного Markdown.'
        },
        auto: {
          label: 'Автоматически',
          tooltip: 'Профилировщик документа сам выбирает между «По заголовкам», «По структуре» и «По длине» разбиением для каждой загрузки.'
        }
      },
      separators: {
        doubleNewline: 'Двойной перевод строки (\\n\\n)',
        singleNewline: 'Одинарный перевод строки (\\n)',
        periodCn: 'Китайская точка (。)',
        exclamationCn: 'Восклицательный знак (！)',
        questionCn: 'Вопросительный знак (？)',
        semicolonCn: 'Китайская точка с запятой (；)',
        semicolonEn: 'Точка с запятой (;)',
        space: 'Пробел ( )'
      }
    },
    models: {
      title: 'Конфигурация моделей',
      description: 'Выберите подходящие AI-модели для базы знаний',
      llmLabel: 'LLM модель',
      llmDesc: 'Большая языковая модель для диалогов и вопросов-ответов',
      llmPlaceholder: 'Выберите LLM модель',
      embeddingLabel: 'Модель встраивания',
      embeddingDesc: 'Модель встраивания для векторизации текста',
      embeddingPlaceholder: 'Выберите модель встраивания',
      embeddingLocked: 'В базе знаний уже есть файлы. Модель встраивания нельзя изменить',
      embeddingOptional: '(необязательно)',
      embeddingWikiOptionalDesc: 'Необязательно. Если задано, используется для сопоставления по сходству при классификации каталога Wiki, чтобы новые страницы лучше повторно использовали существующие папки; иначе классификация выполняется по полному дереву каталога.'
    },
    faqImport: {
      title: 'Пакетный импорт FAQ'
    },
    faq: {
      title: 'Настройки FAQ',
      description: 'Определите стратегию индексации и общие правила для FAQ-базы знаний',
      indexModeLabel: 'Режим индексации',
      indexModeDescription: 'Только вопросы дают более высокую точность, вопросы+ответы повышают полноту выдачи.',
      questionIndexModeLabel: 'Режим индексации вопросов',
      questionIndexModeDescription: 'Объединенная: стандартные и похожие вопросы индексируются вместе. Раздельная: каждый вопрос индексируется независимо для более точного поиска, но требует больше места.',
      entryGuide: 'Каждый FAQ включает основной вопрос, похожие вопросы, негативные примеры и несколько ответов. Управляйте ими в деталях FAQ-базы.',
      modes: {
        questionOnly: 'Только вопросы',
        questionAnswer: 'Вопрос + ответ',
        combined: 'Объединенная',
        separate: 'Раздельная'
      }
    },
    document: {
      title: 'Управление документами'
    },
    messages: {
      loadModelsFailed: 'Не удалось загрузить список моделей',
      loadDataFailed: 'Не удалось загрузить данные базы знаний',
      notFound: 'База знаний не найдена',
      nameRequired: 'Пожалуйста, введите название базы знаний',
      summaryRequired: 'Пожалуйста, выберите модель суммаризации',
      multimodalInvalid: 'Проверка мультимодальной конфигурации не удалась',
      createSuccess: 'База знаний успешно создана',
      createFailed: 'Не удалось создать базу знаний',
      missingId: 'Отсутствует ID базы знаний',
      buildDataFailed: 'Не удалось сформировать данные для отправки',
      updateSuccess: 'Настройки сохранены',
      indexModeRequired: 'Выберите режим индексации для FAQ базы знаний',
      storageChangeConfirm: 'В базе знаний уже есть файлы. Смена хранилища может сделать старые файлы недоступными. Продолжить?'
    },
    share: {
      description: 'Share the knowledge base with spaces so members can access and use it',
      hintTitle: 'Sharing notes',
      addShare: 'Share',
      unshareConfirm: 'Are you sure you want to unshare from "{name}"?',
      tip1: 'After sharing, space members will access this knowledge base based on the assigned permissions',
      tip2: 'Editable permission allows members to modify content; Read-only permission only allows retrieval and Q&A'
    },
    postCreateHint: {
      title: 'База знаний создана',
      footer: 'Продолжите настройку, настройте совместное использование и источники данных, затем нажмите «Сохранить и закрыть».',
      followUpDesc: 'Настройте источники данных слева или опубликуйте базу в пространствах через «Управление общим доступом»'
    },
    footer: {
      instantEffect: 'Изменения на этой странице применяются сразу, сохранять не нужно'
    },
    buttons: {
      create: 'Создать базу знаний',
      saveAndClose: 'Сохранить и закрыть'
    },
    wikiBrowser: {
      viewInGraph: 'Открыть в графе',
      filterSummary: 'Резюме',
      filterEntity: 'Сущности',
      filterConcept: 'Концепции',
      filterSynthesis: 'Синтез',
      filterComparison: 'Сравнения',
      version: 'v{ver}',
      gallery: {
        attr: {
          builtin_caption: 'Описание',
          builtin_caption_description: 'Описание изображения, сгенерированное моделью.',
          builtin_ocr_text: 'OCR-текст',
          builtin_ocr_text_description: 'Текст, извлечённый из изображения OCR.',
          builtin_page: 'Страница документа',
          builtin_page_description: 'Группировка по исходному документу, затем по странице PDF; изображения без номера страницы идут в конце документа.',
          builtin_created_at: 'Время создания',
          builtin_created_at_description: 'Когда был создан фрагмент исходного документа.',
          builtin_updated_at: 'Время изменения',
          builtin_updated_at_description: 'Когда фрагмент исходного документа был изменён последний раз.',
          builtin_is_enabled: 'Состояние',
          builtin_is_enabled_description: 'Участвует ли фрагмент исходного документа в поиске.',
          builtin_is_enabled_value_true: 'Включено',
          builtin_is_enabled_value_false: 'Отключено'
        }
      }
    },
    indexing: {
      title: 'Стратегия индексации',
      description: 'Настройте конвейер обработки после загрузки документов. Каждый способ индексации можно включить или выключить независимо',
      searchTitle: 'RAG-поиск',
      searchDesc: 'Разбивает документы на чанки, векторизует и индексирует ключевые слова, поддерживая гибридный поиск',
      wikiTitle: 'Wiki-база знаний',
      wikiDesc: 'Автоматически создаёт взаимосвязанные Wiki-страницы и формирует структурированную систему знаний',
      atLeastOne: 'Должна быть включена хотя бы одна стратегия индексации',
      embeddingRequired: 'RAG-поиск требует настройки модели Embedding',
      lockedTip: 'В базе знаний уже есть содержимое, изменение стратегии индексации недоступно. Чтобы изменить, сначала очистите базу знаний.',
      rebuildConfirmTitle: 'Перестроить индекс',
      rebuildConfirmBody: 'Стратегия индексации изменена. Переобработать существующие {count} документов? Это может занять некоторое время.',
      rebuildSuccess: 'Задача перестроения отправлена, всего {count} документов',
      rebuildSkip: 'Перестроение можно запустить вручную позже в источниках данных'
    },
    wiki: {
      title: 'Wiki настройки',
      synthesisModelLabel: 'Модель синтеза',
      synthesisModelPlaceholder: 'Выберите LLM модель для генерации Wiki',
      synthesisModelTip: 'Если не указано, используется модель суммаризации',
      autoGenerateLabel: 'Автоматически создавать страницы Wiki',
      autoGenerateTip: 'При отключении страницы Wiki остаются доступными для просмотра и ручного редактирования, но обработка документов не будет вызывать LLM для их создания или обновления',
      extractionGranularityLabel: 'Детализация извлечения',
      contentInstructionsLabel: 'Инструкции для Wiki-контента',
      contentInstructionsTip: 'Задайте акценты и стиль сводок, страниц и индекса. Правила цитирования и слияния остаются системными.',
      contentInstructionsPlaceholder: 'Например: выделять ответственных, сроки и риски…',
      extractionInstructionsLabel: 'Фокус извлечения Wiki',
      extractionInstructionsTip: 'Укажите приоритетные сущности и концепции без замены системного JSON и протокола цитирования.',
      extractionInstructionsPlaceholder: 'Например: продукты, версии, организации, владельцы и ключевые технические концепции…',
      extractionGranularityTip: 'Управляет количеством извлекаемых сущностей/концепций на документ. Точнее — компактный индекс, грубее — более полный',
      granularityFocused: 'Фокус',
      granularityStandard: 'Стандарт',
      granularityExhaustive: 'Полный',
      granularityFocusedHint: 'Извлекает только главные темы документа (например, резюме → человек и его проекты). Самый чистый результат, возможны пропуски.',
      granularityStandardHint: 'Главные темы плюс подробно обсуждаемые сущности/концепции. Пропускает упомянутые вскользь. Рекомендуемое значение.',
      granularityExhaustiveHint: 'Извлекает все именованные сущности и концепции, включая мимоходом упомянутые технологии. Подходит для глоссария.'
    },
    basic: {
      title: 'Основная информация',
      description: 'Укажите название и описание базы знаний',
      kbId: 'ID базы знаний',
      kbIdDesc: 'Используйте этот ID для указания базы знаний в API-интеграциях',
      typeLabel: 'Тип базы знаний',
      typeDocument: 'Документальная',
      typeFAQ: 'FAQ (вопрос-ответ)',
      typeDescription: 'FAQ подходит для структурированных Q&A; документальный тип поддерживает загрузку файлов и разбиение; Wiki автоматически создает связанные страницы знаний через LLM.',
      nameLabel: 'Название базы знаний',
      namePlaceholder: 'Введите название базы знаний',
      descriptionLabel: 'Описание базы знаний',
      descriptionPlaceholder: 'Введите описание базы знаний (необязательно)',
      profile: {
        title: 'Описание, созданное ИИ',
        hint: 'Формируется из агрегата профилей документов. Не заменяет ручное описание выше; агенты читают оба, решая, относится ли вопрос к этой базе знаний.',
        empty: 'Ещё не создано. Загрузите документы, дождитесь их резюме и нажмите кнопку ниже.',
        noDocuments: 'В базе знаний пока нет разобранных документов.',
        questions: 'Типичные вопросы',
        generate: 'Создать описание ИИ',
        regenerate: 'Создать заново',
        adopt: 'Использовать как описание',
        generated: 'Описание ИИ создано',
        generateFailed: 'Не удалось создать описание ИИ',
        adopted: 'Скопировано в описание; сохраните, чтобы применить',
        failed: 'Последняя попытка не удалась: {error}',
        generatedAt: 'Создано {time} · на основе {count} документов'
      }
    },
    errors: {
      vectorStoreBindingInvalid: 'The selected vector store cannot be used. Choose a different store or use the system default.',
      vectorStoreUnavailable: 'The selected vector store is currently unavailable. Check its connection configuration in Settings → Vector Stores.'
    },
    sidebar: {
      basic: 'Основная информация',
      models: 'Конфигурация моделей',
      vectorStore: 'Vector Store',
      chunking: 'Настройки разбиения',
      storage: 'Storage Engine',
      advanced: 'Дополнительные настройки',
      faq: 'FAQ настройки',
      graph: 'Граф знаний',
      multimodal: 'Обработка изображений',
      asr: 'Аудио',
      datasource: 'Источники данных',
      share: 'Sharing',
      activity: 'История активности'
    },
    navGroups: {
      basic: 'Основное',
      processing: 'Индексация и разбор',
      data: 'Хранение и данные',
      integration: 'Публикация',
      management: 'Управление и аудит'
    },
    activity: {
      title: 'История действий',
      description: 'Важные изменения и фоновые задачи этой базы знаний. Срок хранения соответствует политике аудита.',
      allOutcomes: 'Все результаты',
      allActions: 'Все действия',
      refresh: 'Обновить',
      retry: 'Повторить',
      empty: 'Действий пока нет',
      emptyFiltered: 'Нет подходящих записей активности',
      clearFilters: 'Сбросить фильтры',
      loadingMore: 'Загрузка…',
      end: 'Более ранних записей нет',
      loadFailed: 'Не удалось загрузить историю',
      systemActor: 'Система',
      actorWithAPIKey: '{actor} · API Key · {name}',
      actorAPIKey: 'API Key · {name}',
      viaAssistant: 'Через ассистента Xiaozhi',
      knowledgeBase: 'База знаний',
      countItems: '{count} элем.',
      titleWithCount: '{title} и ещё {count}',
      importSummary: 'Успешно {success} / Ошибок {failed} / Пропущено {skipped}',
      detailValues: {
        user: 'Запущено пользоватем',
        manual: 'Вручную',
        schedule: 'По расписанию',
        system: 'Система',
        pending: 'Ожидает',
        completed: 'Завершено',
        partial: 'Частично завершено',
        canceled: 'Отменено',
        failed: 'Ошибка',
        enqueue: 'Постановка в очередь',
        reuse_vectors: 'Повторное использование векторов',
        reparse: 'Повторный разбор',
        viewer: 'Только чтение',
        editor: 'Редактирование',
        admin: 'Управление',
        append: 'Добавление',
        replace: 'Замена'
      },
      outcomes: {
        accepted: 'Принято',
        success: 'Успешно',
        failed: 'Ошибка',
        partial: 'Частично',
        canceled: 'Отменено',
        denied: 'Отклонено'
      },
      actions: {
        'kb.created': 'База знаний создана',
        'kb.updated': 'База знаний обновлена',
        'kb.deleted': 'База знаний удалена',
        'kb.duplicated': 'База знаний скопирована',
        'kb.clone_started': 'Клонирование начато',
        'kb.clone_completed': 'Клонирование завершено',
        'kb.clone_failed': 'Ошибка клонирования',
        'knowledge.created': 'Знание добавлено',
        'knowledge.updated': 'Знание обновлено',
        'knowledge.deleted': 'Знание удалено',
        'knowledge.batch_deleted': 'Знания удалены пакетом',
        'knowledge.reparse_started': 'Повторный разбор начат',
        'knowledge.parse_canceled': 'Разбор отменён',
        'knowledge.move_started': 'Перемещение начато',
        'knowledge.move_completed': 'Перемещение завершено',
        'knowledge.move_failed': 'Ошибка перемещения',
        'tag.created': 'Тег создан',
        'tag.updated': 'Тег обновлён',
        'tag.deleted': 'Тег удалён',
        'datasource.created': 'Источник данных создан',
        'datasource.updated': 'Источник данных обновлён',
        'datasource.deleted': 'Источник данных удалён',
        'datasource.sync_started': 'Синхронизация начата',
        'datasource.sync_completed': 'Синхронизация завершена',
        'datasource.sync_failed': 'Ошибка синхронизации',
        'datasource.paused': 'Источник приостановлен',
        'datasource.resumed': 'Источник возобновлён',
        'kb.share_added': 'Общий доступ добавлен',
        'kb.share_permission_changed': 'Права доступа изменены',
        'kb.share_removed': 'Общий доступ удалён',
        'wiki.content_changed': 'Содержимое Wiki обновлено',
        'faq.import_started': 'Импорт FAQ начат',
        'faq.import_completed': 'Импорт FAQ завершён',
        'faq.import_failed': 'Ошибка импорта FAQ'
      },
      detailFields: {
        task_id: 'ID задачи',
        trigger: 'Запуск',
        processing_status: 'Статус обработки',
        source_kb_id: 'ID исходной базы',
        target_kb_id: 'ID целевой базы',
        sync_log_id: 'ID журнала синхронизации',
        mode: 'Режим',
        attempt: 'Попытка',
        count: 'Количество',
        total: 'Всего',
        processed: 'Обработано',
        failed: 'Ошибок',
        skipped: 'Пропущено',
        failure_stage: 'Этап ошибки'
      },
      targets: {
        knowledge_base: 'База знаний',
        knowledge: 'Знание',
        faq_entry: 'FAQ',
        knowledge_tag: 'Тег',
        data_source: 'Источник данных',
        knowledge_base_share: 'Общий доступ',
        knowledge_move: 'Перемещение',
        wiki: 'Wiki'
      },
      drawer: {
        sectionSummary: 'Сводка',
        sectionIdentifiers: 'Идентификаторы',
        sectionTask: 'Информация о задаче',
        targetChange: 'Детали изменения'
      },
      expanded: {
        targetType: 'Тип объекта',
        targetId: 'ID объекта',
        actorId: 'ID инициатора',
        apiKeyName: 'Имя API-ключа',
        apiKeyId: 'ID API-ключа',
        agentSessionId: 'ID диалога ассистента',
        agentOperation: 'Операция ассистента',
        details: 'Подробности'
      },
      columns: {
        time: 'Время',
        action: 'Действие',
        target: 'Объект',
        actor: 'Инициатор',
        outcome: 'Результат'
      }
    }
  },
  embedPublish: {
    copyCode: 'Копировать код'
  },
  knowledgeList: {
    detail: {
      title: 'Shared Knowledge Base',
      sourceOrg: 'Space',
      myPermission: 'My Permission'
    },
    sections: {
      tenantOthers: 'Рабочая область · Другие участники',
      tenantReadonly: 'Рабочая область · Только просмотр'
    },
    empty: {
      title: 'Базы знаний отсутствуют'
    }
  },
  createChat: {
    title: 'Привет, я Xiaozhi — ваши знания всегда под рукой',
    newSessionTitle: 'Новая сессия',
    openProject: 'Выбрать проект',
    clearProject: 'Снять привязку',
    pickFailed: 'Не удалось открыть выбранный путь',
    messages: {
      createFailed: 'Не удалось создать сессию',
      createError: 'Не удалось создать сессию, попробуйте позже'
    }
  },
  input: {
    addModel: 'Добавить модель',
    placeholder: 'Задайте вопрос или опишите задачу…',
    agentMode: 'Умный анализ',
    normalMode: 'Быстрый ответ',
    normalModeDesc: 'RAG-вопросы и ответы по базе знаний',
    agentModeDesc: 'Многошаговое мышление, глубокий анализ',
    agentMissingAllowedTools: 'Разрешённые инструменты',
    agentMissingSummaryModel: 'Модель беседы',
    agentMissingRerankModel: 'Модель переранжирования',
    customAgentMissingSummaryModel: 'Модель беседы',
    customAgentMissingRerankModel: 'Модель переранжирования',
    goToAgentEditor: 'Go to configure →',
    agentNotReadyDetail: 'Agent не готов. Пожалуйста, настройте следующее: {reasons}',
    sharedAgentNotReadyDetail: 'Общий agent «{agentName}» не готов (отсутствует: {reasons}). Обратитесь к администратору организации, которая поделилась agent.',
    knowledgeBase: 'База знаний',
    knowledgeBaseWithCount: 'База знаний ({count})',
    notConfigured: 'Не настроено',
    sharedAgentModelLabel: 'Модель из общего агента',
    noModel: 'Нет доступных моделей',
    modelAuto: 'По умолчанию',
    modelFollowDefault: 'Как по умолчанию',
    modelAutoHint: 'Модель чата текущей базы знаний, а вне базы знаний или если она не задана — первая доступная модель чата',
    stopGeneration: 'Остановить генерацию',
    send: 'Отправить',
    steerRetry: 'Повторить отправку',
    webSearchDisabledByAgent: 'Web search is disabled by the current agent',
    kbLockedByAgent: 'Knowledge base configuration is locked by the current agent',
    kbDisabledByAgent: 'Knowledge base is disabled by the current agent',
    modelLockedByAgent: 'Model selection is locked by the current agent',
    imageUploadDisabledByAgent: 'Image upload is not enabled for this agent',
    voiceTooltip: 'Удерживайте, чтобы говорить ({shortcut})',
    voicePreparing: 'Микрофон включается, начните говорить, когда кнопка станет красной',
    voiceRecording: 'Идёт запись, отпустите для завершения',
    voiceReleasedEarly: 'Микрофон ещё не был готов. Удерживайте, пока кнопка не станет красной, затем говорите',
    voiceTranscribing: 'Распознавание речи…',
    voiceUnsupported: 'Этот браузер не поддерживает запись звука',
    voiceInsecureContext: 'Голосовой ввод доступен только по HTTPS или на localhost',
    voicePermissionDenied: 'Нет доступа к микрофону. Разрешите его в настройках браузера',
    voiceDeviceError: 'Микрофон не найден',
    voiceDecodeError: 'Не удалось обработать запись. Попробуйте ещё раз',
    voiceTranscribeFailed: 'Не удалось распознать речь. Проверьте настройки ASR-модели агента',
    voiceEmptyResult: 'Речь не распознана',
    goToAgentSettings: 'Go to agent settings',
    hostApprovalMode: {
      ask: 'Спрашивать меня',
      askHint: 'Удаление и запись вне рабочей области требуют вашего подтверждения',
      auto: 'Одобрять за меня',
      autoHint: 'Модель решает за вас, не отвлекая',
      switchFailed: 'Не удалось сменить режим одобрения'
    },
    messages: {
      enterContent: 'Сначала введите содержимое!',
      replying: 'Ответ формируется, попробуйте позже!',
      steerFailed: 'Не удалось добавить сообщение. Попробуйте ещё раз.',
      agentSwitchedOn: 'Переключено в Agent режим',
      agentSwitchedOff: 'Переключено в обычный режим',
      agentSelected: 'Selected agent "{name}"',
      webSearchNotConfigured: 'Веб-поиск не настроен. Сначала выберите провайдера и настройте ключи в разделе настроек.',
      webSearchEnabled: 'Веб-поиск включён',
      webSearchDisabled: 'Веб-поиск выключен',
      sessionMissing: 'ID сессии не существует',
      messageMissing: 'Не удалось получить ID сообщения. Обновите страницу и попробуйте снова.',
      stopSuccess: 'Генерация остановлена',
      stopFailed: 'Не удалось остановить. Попробуйте ещё раз.'
    },
    webSearch: {
      toggleOn: 'Включить веб-поиск',
      toggleOff: 'Выключить веб-поиск',
      notConfigured: 'Веб-поиск не настроен'
    }
  },
  manualEditor: {
    defaultTitlePrefix: 'Новый документ',
    noDocumentKnowledgeBases: 'Нет доступных баз знаний типа "документ". Пожалуйста, создайте одну сначала',
    actions: {
      cancel: 'Отмена',
      saveDraft: 'Сохранить черновик',
      publish: 'Опубликовать'
    },
    loading: {
      content: 'Загрузка содержимого...',
      preparing: 'Подготовка редактора...'
    },
    status: {
      draftTag: 'Статус: Черновик',
      publishedTag: 'Статус: Опубликовано',
      lastUpdated: 'Последнее обновление: {time}',
      counter: 'Символов: {chars} · Строк: {lines}'
    },
    form: {
      knowledgeBasePlaceholder: 'Выберите базу знаний',
      titleLabel: 'Заголовок знания',
      knowledgeBaseLabel: 'Целевая база знаний',
      titlePlaceholder: 'Введите заголовок',
      contentPlaceholder: 'Поддерживается Markdown. Используйте # заголовки, списки, блоки кода и т.д.'
    },
    success: {
      draftSaved: 'Черновик сохранён',
      published: 'Знание опубликовано и начата индексация'
    },
    warning: {
      selectKnowledgeBase: 'Пожалуйста, выберите целевую базу знаний',
      enterTitle: 'Введите заголовок знания',
      enterContent: 'Введите содержимое знания',
      contentTooShort: 'Контент слишком короткий. Добавьте больше информации перед публикацией'
    },
    error: {
      fetchDetailFailed: 'Не удалось получить сведения о знании',
      saveFailed: 'Не удалось сохранить, попробуйте позже'
    },
    labels: {
      currentKnowledgeBase: 'Текущая база знаний'
    },
    section: {
      content: 'Содержимое'
    },
    title: {
      edit: 'Редактировать Markdown-знание',
      create: 'Создать Markdown-знание'
    },
    preview: {
      empty: 'Пока нет содержимого'
    },
    view: {
      edit: 'Редактор',
      split: 'Разделить',
      preview: 'Предпросмотр',
      splitUnavailable: 'Расширьте панель или включите полный экран, чтобы разделить вид',
      groupLabel: 'Вид редактора'
    },
    shortcuts: {
      title: 'Горячие клавиши',
      continueList: 'Продолжить список',
      indent: 'Отступ / Shift+Tab — назад'
    },
    toolbar: {
      bold: 'Жирный',
      italic: 'Курсив',
      strike: 'Зачёркнутый',
      inlineCode: 'Встроенный код',
      heading1: 'Заголовок 1',
      heading2: 'Заголовок 2',
      heading3: 'Заголовок 3',
      bulletList: 'Маркированный список',
      orderedList: 'Нумерованный список',
      taskList: 'Список задач',
      blockquote: 'Цитата',
      codeBlock: 'Блок кода',
      link: 'Вставить ссылку',
      image: 'Вставить изображение',
      table: 'Вставить таблицу',
      horizontalRule: 'Горизонтальная линия',
      headingGroup: 'Заголовок',
      insertGroup: 'Вставить'
    },
    table: {
      column1: 'Колонка 1',
      column2: 'Колонка 2',
      cell: 'Содержимое'
    },
    placeholders: {
      heading: 'Заголовок {level}',
      listItem: 'Элемент списка',
      taskItem: 'Задача',
      quote: 'Текст цитаты',
      code: 'Содержимое кода',
      linkText: 'Текст ссылки',
      imageAlt: 'Описание',
      bold: 'Жирный текст',
      italic: 'Курсив',
      strike: 'Зачеркнутый текст',
      inlineCode: 'code'
    },
    assistant: {
      button: 'Ассистент',
      tooltip: 'Попросить ассистента помочь с текстом',
      continue: 'Продолжить текст',
      outline: 'Составить план',
      polish: 'Улучшить текст',
      summarize: 'Кратко изложить',
      open: 'Открыть ассистента',
      prompts: {
        continue: 'Продолжи текст с конца ещё одним абзацем, связанным с предыдущим.',
        outline: 'Составь по заголовку и текущему тексту чёткий план документа и вставь его в начало текста.',
        polish: 'Улучши текст: исправь опечатки и неудачные предложения, не меняя смысла, по разделам.',
        summarize: 'Кратко изложи основные мысли документа в чате. Текст не меняй.'
      }
    }
  },
  file: {
    upload: 'Загрузить файл'
  },
  mentionDetail: {
    readOnlyFromAgent: 'Только чтение (от агента)',
    faqCount: '{count} вопросов и ответов',
    kbCount: '{count} документов',
    mcpToolCount: '{count} инструментов',
    mcpNotSynced: 'Инструменты ещё не синхронизированы',
    mcpStale: 'Нужна повторная синхронизация',
    belongsToKb: 'База знаний: ',
    belongsToOrg: 'Пространство: ',
    noCompatibleKbForAgent: 'Инструменты текущего агента не соответствуют возможностям ни одной базы знаний в области видимости — нечего упомянуть.',
    tag: 'Теги',
    searchPlaceholder: 'Поиск баз, файлов, навыков…',
    searchInGroup: 'Поиск в разделе «{group}»…',
    typeToSearch: 'Продолжайте ввод после {\'@\'} для поиска…',
    viewAll: 'Показать все',
    back: 'Назад'
  },
  mentionBrowser: {
    browse: 'Обзор по папкам',
    path: 'Путь к папке',
    root: 'Корень',
    searchFolder: 'Поиск в этой папке',
    searchKb: 'Поиск баз знаний',
    subtree: 'Поиск включает вложенные папки.',
    wholeKb: 'Выбрана вся база знаний; выбор файла не сужает область поиска.',
    tags: 'Существующие теги продолжают фильтровать выбранные файлы.',
    folderCount: 'Документов с учётом вложенных папок: {count}',
    selected: 'Уже выбран',
    deleting: 'Удаляется',
    unsupported: 'Формат не поддерживается агентом',
    forbidden: 'У вас больше нет доступа к этому содержимому.',
    missing: 'Папка недоступна. Вернитесь и выберите её снова.',
    error: 'Не удалось загрузить папку. Повторите попытку.',
    retry: 'Повторить',
    empty: 'В этом представлении нет файлов.',
    previous: 'Назад',
    next: 'Далее',
    page: 'Страница {page} · документов: {total}'
  },
  common: {
    confirm: 'Подтвердить',
    cancel: 'Отмена',
    fullscreen: 'Полный экран',
    exitFullscreen: 'Выйти из полного экрана',
    save: 'Сохранить',
    delete: 'Удалить',
    edit: 'Редактировать',
    copy: 'Копировать',
    copied: 'Скопировано',
    copySuccess: 'Успешно скопировано',
    loading: 'Загрузка...',
    noMoreData: 'Весь контент загружен',
    loadMore: 'Загрузить ещё',
    error: 'Ошибка',
    success: 'Успешно',
    failed: 'Ошибка',
    selectAll: 'Выбрать все',
    yes: 'Да',
    no: 'Нет',
    close: 'Закрыть',
    back: 'Назад',
    next: 'Далее',
    finish: 'Завершить',
    all: 'Все',
    clear: 'Очистить',
    on: 'Вкл',
    off: 'Выкл',
    confirmDelete: 'Подтвердить удаление',
    deleteFailed: 'Ошибка удаления',
    operationFailed: 'Операция не выполнена',
    file: 'Файл',
    skill: 'Навыки',
    knowledgeBase: 'База знаний',
    noResult: 'Нет результатов',
    remove: 'Удалить',
    avatar: 'Аватар',
    defaultUser: 'Пользователь',
    copyFailed: 'Ошибка копирования',
    retry: 'Повторить',
    expand: 'Развернуть',
    unsavedChanges: {
      title: 'Несохранённые изменения',
      body: 'Если закрыть сейчас, изменения будут потеряны. Закрыть?',
      discard: 'Отменить изменения',
      keepEditing: 'Продолжить редактирование'
    }
  },
  authStore: {
    errors: {
      parseUserFailed: 'Не удалось разобрать данные пользователя',
      parseTenantFailed: 'Не удалось разобрать данные пространства',
      parseKnowledgeBasesFailed: 'Не удалось разобрать список баз знаний',
      parseCurrentKnowledgeBaseFailed: 'Не удалось разобрать текущую базу знаний'
    }
  },
  auth: {
    account: 'Логин',
    accountPlaceholder: 'Введите логин',
    accountRequired: 'Введите логин',
    accountDescription: 'Учётная запись для входа на платформу',
    login: 'Вход',
    logout: 'Выход',
    oidcLogin: 'Войти через OIDC',
    oidcLoginWithProvider: 'Войти через {provider}',
    redirectingToOIDC: 'Перенаправление к поставщику удостоверений...',
    orContinueWith: 'Или продолжить с помощью',
    oidcLoginFailed: 'Ошибка входа через OIDC',
    username: 'Имя пользователя',
    email: 'Почта Email',
    password: 'Пароль',
    confirmPassword: 'Подтвердите пароль',
    loginSuccessTitle: 'Вход выполнен',
    loginSuccessContent: 'С возвращением. Вы вошли в {name}',
    loggingIn: 'Вход...',
    register: 'Регистрация',
    registering: 'Регистрация...',
    createAccount: 'Создать аккаунт',
    haveAccount: 'Уже есть аккаунт?',
    backToLogin: 'Вернуться ко входу',
    loginHint: 'Войдите, чтобы продолжить, или создайте аккаунт ниже, если вы впервые здесь.',
    firstTime: 'Впервые здесь?',
    registerSuccess: 'Регистрация завершена. Войдите в систему',
    registerFailed: 'Ошибка регистрации',
    registerSubtitle: 'Создайте аккаунт, чтобы начать работу',
    emailPlaceholder: 'Введите адрес электронной почты',
    passwordPlaceholder: 'Введите пароль',
    confirmPasswordPlaceholder: 'Введите пароль ещё раз',
    usernamePlaceholder: 'Введите имя пользователя',
    emailRequired: 'Введите адрес электронной почты',
    emailInvalid: 'Введите правильный формат электронной почты',
    passwordRequired: 'Введите пароль',
    passwordMinLength: 'Пароль должен быть не менее 8 символов',
    passwordMaxLength: 'Пароль не может превышать 1024 символа',
    passwordMustContainLetter: 'Пароль должен содержать буквы',
    passwordMustContainLowercaseLetter: 'Пароль должен содержать строчные буквы',
    passwordMustContainUppercaseLetter: 'Пароль должен содержать прописные буквы',
    passwordMustContainNumber: 'Пароль должен содержать цифры',
    passwordMustContainSpecialChar: 'Пароль должен содержать специальные символы: {specialChars}',
    usernameRequired: 'Введите имя пользователя',
    usernameMinLength: 'Имя пользователя должно быть не менее 2 символов',
    usernameMaxLength: 'Имя пользователя не может превышать 20 символов',
    usernameInvalid: 'Имя пользователя может содержать только буквы, цифры, подчёркивания и китайские иероглифы',
    confirmPasswordRequired: 'Подтвердите пароль',
    passwordMismatch: 'Введённые пароли не совпадают',
    loginError: 'Ошибка входа, проверьте логин или пароль',
    loginErrorRetry: 'Ошибка входа, пожалуйста, повторите попытку позже',
    registerError: 'Ошибка регистрации, пожалуйста, повторите попытку позже',
    workspaceOnboarding: {
      title: 'Выберите рабочее пространство',
      description: 'Создайте личное пространство, чтобы продолжить.',
      create: 'Создать пространство',
      invitations: 'Посмотреть приглашения',
      loadingPolicy: 'Проверяем доступные способы присоединения…',
      policyLoadFailed: 'Не удалось загрузить разрешения пространства. Проверьте подключение и повторите попытку.',
      retry: 'Повторить',
      inviteOnlyTitle: 'Ожидание приглашения в пространство',
      inviteOnlyDescription: 'Создание личных пространств отключено. Просмотрите и примите приглашение администратора.',
      inviteOnlyNotice: 'Этот аккаунт может присоединиться к существующему пространству только по приглашению',
      help: 'Вы можете создать рабочее пространство сейчас или вернуться позже, чтобы принять приглашение.',
      inviteOnlyHelp: 'Нет приглашения? Сообщите администратору пространства свой регистрационный адрес электронной почты.'
    }
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
  initialization: {
    skip: 'Пропустить',
    next: 'Далее'
  },
  graphSettings: {
    title: 'Настройки графа знаний',
    description: 'Настройте извлечение сущностей и отношений для автоматического построения графа знаний из текста (примечание: это не то же самое, что «граф ссылок страниц» внутри Wiki — там показаны связи между Wiki-страницами, а здесь строится граф сущностей и отношений на основе LLM)',
    enableLabel: 'Включить извлечение сущностей и отношений',
    enableDescription: 'Автоматически извлекать сущности и отношения из текста при включении',
    tagsLabel: 'Типы отношений',
    tagsDescription: 'Определите теги типов отношений для извлечения, разделённые запятыми',
    tagsPlaceholder: 'Введите типы отношений, например: работает_в, коллега, друг',
    generateRandomTags: 'Сгенерировать случайные теги',
    sampleTextLabel: 'Образец текста',
    sampleTextDescription: 'Образец текста для тестирования извлечения сущностей и отношений',
    sampleTextPlaceholder: 'Введите текст, содержащий сущности и отношения...',
    customInstructionsLabel: 'Дополнительные инструкции извлечения',
    customInstructionsDescription: 'Добавьте предметную область и правила атрибутов, сохраняя системный формат вывода',
    customInstructionsPlaceholder: 'Например: уделять внимание сторонам договора, суммам, срокам и ответственности…',
    generateRandomText: 'Сгенерировать случайный текст',
    entityListLabel: 'Список сущностей',
    entityListDescription: 'Сущности и их атрибуты, извлечённые из текста',
    nodeNamePlaceholder: 'Введите имя сущности',
    attributePlaceholder: 'Введите значение атрибута',
    addAttribute: 'Добавить атрибут',
    manageEntitiesLabel: 'Управление сущностями',
    manageEntitiesDescription: 'Добавить или удалить узлы сущностей',
    addEntity: 'Добавить сущность',
    relationListLabel: 'Список отношений',
    relationListDescription: 'Определите связи отношений между сущностями',
    selectEntity: 'Выберите сущность',
    selectRelationType: 'Выберите тип отношения',
    manageRelationsLabel: 'Управление отношениями',
    manageRelationsDescription: 'Добавить или удалить отношения между сущностями',
    addRelation: 'Добавить отношение',
    extractActionsLabel: 'Действия извлечения',
    extractActionsDescription: 'Выполнить извлечение сущностей и отношений или управлять образцами данных',
    startExtraction: 'Начать извлечение',
    extracting: 'Извлечение...',
    defaultExample: 'Пример по умолчанию',
    clearExample: 'Очистить пример',
    completeModelConfig: 'Пожалуйста, сначала завершите настройку модели',
    tagsGenerated: 'Теги успешно сгенерированы',
    tagsGenerateFailed: 'Не удалось сгенерировать теги',
    textGenerated: 'Текст успешно сгенерирован',
    textGenerateFailed: 'Не удалось сгенерировать текст',
    pleaseInputText: 'Пожалуйста, сначала введите образец текста',
    extractSuccess: 'Извлечение сущностей и отношений выполнено успешно',
    extractFailed: 'Не удалось извлечь сущности и отношения',
    exampleLoaded: 'Пример загружен',
    exampleCleared: 'Пример очищен',
    checkingAvailability: 'Проверка доступности графа знаний…',
    checkAvailabilityFailed: 'Не удалось проверить доступность графа знаний. Повторите попытку.',
    disabledWarning: 'База данных графа знаний не включена, извлечение сущностей и отношений будет недоступно',
    howToEnable: 'Как включить граф знаний?'
  },
  retrievalSettings: {
    title: 'Настройки поиска',
    description: 'Настройте глобальные параметры поиска, общие для поиска по знаниям и сообщениям; значения передаются напрямую в официальный API запросов ContextDB',
    topKLabel: 'Результатов на запрос (Top K)',
    topKDescription: 'Количество фрагментов за один запрос, диапазон 1–10; официальное значение ContextDB по умолчанию — 5',
    similarityThresholdLabel: 'Порог сходства',
    similarityThresholdDescription: 'Фрагменты ниже этой релевантности отфильтровываются, диапазон 0–1; официальное значение ContextDB по умолчанию — 0.6',
    vectorWeightLabel: 'Вес векторного поиска',
    vectorWeightDescription: 'Баланс между векторным и ключевым поиском, диапазон 0–1; официальное значение ContextDB по умолчанию — 0.7',
    queryRewriteLabel: 'Переписывание запроса',
    queryRewriteDescription: 'ContextDB переписывает запрос с помощью LLM перед поиском; официально выключено по умолчанию, здесь включено',
    toasts: {
      saveSuccess: 'Конфигурация поиска сохранена',
      saveFailed: 'Не удалось сохранить конфигурацию: {message}'
    }
  },
  defaultSettings: {
    saving: 'Сохранение',
    loadFailed: 'Не удалось загрузить настройки по умолчанию. Повторите попытку перед редактированием.',
    title: 'Значения по умолчанию',
    readOnly: 'Изменять может только администратор пространства. Вы можете посмотреть, какие значения действуют сейчас.',
    webSearchGroup: 'Веб-поиск',
    toasts: {
      saveFailed: 'Не удалось сохранить: {message}'
    },
    webSearch: {
      label: 'Поисковая система по умолчанию',
      description: 'Используется, когда у агента включён веб-поиск, но не выбрана своя поисковая система.',
      unset: 'Поисковая система по умолчанию не задана. Агенты без своей поисковой системы не смогут искать в интернете.',
      placeholder: 'Выберите поисковую систему'
    },
    hints: {
      workspace: 'Используется настройка пространства.',
      system: 'Не задано. Сейчас используется системное значение: {name}',
      auto: 'Не задано. Сейчас используется первая доступная модель: {name}',
      followChat: 'Не задано. Как модель чата по умолчанию: {name}',
      staleFallback: 'Выбранная модель удалена или недоступна. Сейчас используется: {name}',
      staleNone: 'Выбранная модель удалена или недоступна, и заменить её нечем.'
    },
    slots: {
      asr: {
        label: 'Модель распознавания речи по умолчанию',
        description: 'Выбор по умолчанию для транскрипции аудио и видео.',
        none: 'Нет доступной модели распознавания речи: транскрипция недоступна.'
      },
      vlm: {
        label: 'Модель зрения по умолчанию',
        description: 'Выбор по умолчанию для понимания изображений и мультимодального разбора.',
        none: 'Нет доступной модели зрения: понимание изображений недоступно.'
      },
      rerank: {
        label: 'Модель реранжирования по умолчанию',
        description: 'Для поиска и встроенных агентов без собственной модели реранжирования.',
        none: 'Нет доступной модели реранжирования: результаты возвращаются в порядке извлечения.'
      },
      embedding: {
        label: 'Модель эмбеддингов по умолчанию',
        description: 'Выбирается по умолчанию при создании базы знаний. Существующие базы не меняются.',
        none: 'Нет доступной модели эмбеддингов: создать базу знаний нельзя.'
      },
      utility: {
        label: 'Лёгкая модель генерации',
        description: 'Для коротких задач: заголовки сессий, инструкции к сервисам MCP. Подойдёт более быстрая и дешёвая модель.',
        none: 'Нет доступной модели чата: заголовки и инструкции не будут генерироваться.'
      },
      chat: {
        label: 'Модель чата по умолчанию',
        description: 'Используется новыми агентами и в вопросах-ответах, а также как резервная для фоновых задач.',
        none: 'Нет доступной модели чата: вопросы-ответы и фоновая генерация не будут работать.'
      }
    }
  },
  envVarSettings: {
    host: {
      title: 'Переменные среды'
    }
  },
  settings: {
    modelManagement: 'Управление моделями',
    autoCheckUpdate: 'Автоматическая загрузка обновлений',
    autoCheckUpdateDesc: 'При включении автоматически проверять и скачивать последнюю версию в фоновом режиме при запуске.',
    parserEngine: 'Движок парсинга',
    mcpService: 'Сервис MCP',
    workspaceSettings: 'Настройки пространства',
    capabilityUnavailable: 'Эта функция не поддерживается в текущем развёртывании. Выполнен переход на доступную страницу.',
    hostApprovalDefault: {
      title: 'Одобрение действий по умолчанию',
      description: 'Когда агент удаляет файлы или пишет вне рабочей области, здесь выбирается: спрашивать вас каждый раз или пусть решает модель. Новые чаты начинают отсюда; в текущем чате режим меняется слева от поля ввода.'
    },
    storage: {
      title: 'Хранилище',
      engineLocal: 'Локальное',
      engineCos: 'Tencent Cloud COS',
      engineTos: 'Volcengine TOS',
      engineOss: 'Alibaba Cloud OSS'
    },
    parser: {
      title: 'Парсер'
    },
    roleDenied: {
      title: 'Недостаточно прав',
      desc: 'Ваша роль не позволяет открыть этот раздел настроек. Обратитесь к администратору пространства, чтобы запросить нужную роль.'
    },
    navGroups: {
      systemAdministration: 'Системное администрирование'
    },
    skills: {
      nativeUsage: 'Select packages in the agent configuration. Scripts require OpenSandbox and suitable dependencies; a catalog entry does not prove dependencies are installed.',
      addSourceDescription: 'Import a directory containing one SKILL.md, references and scripts. Importing records content and does not execute an installer.',
      title: 'Управление навыками',
      description: 'Manage skill packages. Selected instructions and references are loaded by SkillsMiddleware; uploading does not install dependencies.',
      helpTooltip: 'The catalog holds instructions, references and scripts. Scripts run in the session sandbox; dependencies come from its deployed image.',
      addSkill: 'Добавить навык',
      addStepRegister: 'Регистрация',
      addFileSelected: 'Выбран {name}',
      addClearFile: 'Очистить',
      emptyDesc: 'No skill packages yet. Upload a ZIP or add a source.',
      deleteCatalog: 'Удалить из каталога',
      deleteCatalogConfirm: 'Delete “{name}” from the catalog? Historical installation records remain; referenced entries cannot be deleted.',
      deleteSuccess: 'Удалено из каталога',
      registerAccepted: 'Добавлено в каталог',
      loadFailed: 'Не удалось загрузить'
    },
    sandbox: {
      title: 'Настройка песочницы',
      skillUploadClick: 'Нажмите, чтобы загрузить zip',
      skillUploadDrag: 'или перетащите файл сюда',
      skillSourceSection: 'Установить из источника',
      skillSourceSectionHint: 'Вставьте ссылку ClawHub, GitHub или SkillHub, либо {\'@\'}owner/slug. Архив не может превышать {size} МБ.',
      skillUploadSection: 'Загрузить локальный пакет',
      skillUploadSectionHint: 'Перетащите zip с файлом SKILL.md ниже или нажмите, чтобы выбрать файл. Архив не может превышать {size} МБ.',
      skillSourcePlaceholder: 'ClawHub: {\'@\'}owner/slug. GitHub/SkillHub: вставьте полный URL',
      skillSourceFailed: 'Не удалось установить навык из реестра',
      skillUploadFailed: 'Failed to upload the skill',
      skillBundleTooLarge: 'Архив навыка не может превышать {size} МБ.',
      skillBundleTooManyFiles: 'В каталоге навыка не может быть больше {count} файлов.',
      skillBundleTooManyZipEntries: 'В архиве не может быть больше {count} записей.',
      installCommandRunning: 'Команда выполняется',
      skillFiles: 'Просмотреть файлы',
      skillFilesTitle: 'Файлы',
      skillFilesEmpty: 'У этого навыка пока нет файлов для просмотра.',
      skillFilesLoadFailed: 'Не удалось загрузить файлы навыка',
      skillFilesFileLoadFailed: 'Не удалось прочитать этот файл',
      skillFilesBinary: 'Это двоичный файл, его нельзя просмотреть.',
      skillFilesTruncated: 'Файл слишком большой, показана только начальная часть.',
      skillFilesSelectHint: 'Выберите файл слева, чтобы просмотреть содержимое',
      skillFilesPreview: 'Просмотр',
      skillFilesSource: 'Исходник',
      skillDisabled: 'Skill disabled',
      installCommandWaiting: 'Ожидание вывода команды. Время выполнения обновляется.'
    }
  },
  agent: {
    taskLabel: 'Задача:',
    think: 'Размышление',
    copy: 'Копировать',
    addToKnowledgeBase: 'Добавить в базу знаний',
    updatePlan: 'Обновить план',
    webSearchFound: 'Найдено <strong>{count}</strong> результатов веб‑поиска',
    toolFallback: 'Инструмент',
    stepsCompleted: 'Выполнено <strong>{steps}</strong> шаг(ов)',
    reasoningRounds: '<strong>{rounds}</strong> раунд(ов) рассуждений',
    earlierSteps: 'Предыдущие шаги: {count}',
    viewReasoning: 'Показать рассуждения',
    toolCalls: '<strong>{tools}</strong> вызов(ов) инструментов',
    durationSuffix: '<strong>{duration}</strong>',
    stepSummarySeparator: ' · ',
    contextCompacted: 'Контекст сжат',
    contextCompactedSummary: '{before} → {after} токенов',
    contextCompactedDegraded: 'Сводка недоступна, сохранена исходная запись',
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
    selector: {
      title: 'Select Agent',
      current: 'Current',
      goToSettings: 'Settings',
      sharedLabel: 'Shared',
      notReadyHint: 'Still needs: {items}',
      notReadyStatus: 'Setup needed',
      configureAction: 'Configure',
      sharedNotReadyContact: 'Ask the sharing organization admin to finish setup',
      capabilitiesSection: 'Возможности',
      webSearchCapability: 'Web search',
      imageUploadCapability: 'Image upload',
      capabilityEnabled: 'On',
      capabilityDisabled: 'Off',
      capabilitySupported: 'Supported',
      capabilityUnsupported: 'Unsupported',
      capabilityUnconfigured: 'Not set'
    },
    editor: {
      assistantChanged: 'Ассистент изменил этого агента. Откройте его заново, чтобы увидеть актуальные настройки.',
      assistantDeleted: 'Ассистент удалил этого агента.',
      reasoningEffortUnsupported: 'Выбранная модель не поддерживает размышления; все варианты, кроме «Выкл», игнорируются.',
      reasoningEffortAlwaysOn: 'Выбранная модель всегда размышляет, её нельзя отключить — можно менять только уровень усилий.',
      createTitle: 'Create Agent',
      editTitle: 'Edit Agent',
      basicInfo: 'Basic Info',
      basicInfoDesc: 'Настройка имени, описания и режима работы агента',
      promptsConfig: 'Промпты',
      promptsConfigDesc: 'Настройка системных, контекстных, intent/rewrite/fallback промптов',
      modelConfig: 'Model Config',
      modelConfigDesc: 'Модель чата, вспомогательные модели (ReRank) и параметры генерации',
      toolsConfig: 'Tools',
      toolsConfigDesc: 'Configure tools available to the Agent',
      knowledgeConfig: 'Knowledge Base',
      knowledgeConfigDesc: 'Настройка области баз знаний и стратегии FAQ для агента',
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
      citationEnabled: 'Показывать ссылки на источники',
      citationEnabledDesc: 'Показывать источники базы знаний и веб-страниц в итоговом ответе; поиск продолжает работать и при отключении',
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
      rerankModelOptionalHint: 'В текущей области нет RAG-базы знаний, поэтому поле необязательное. Если RAG-база будет добавлена позже, будет использоваться модель ReRank по умолчанию для пространства; всё же рекомендуется настроить её явно.',
      maxIterations: 'Лимит вызовов модели основным агентом',
      maxIterationsLimit: 'Лимит',
      maxIterationsUnlimited: 'Без ограничения',
      allowedTools: 'Allowed Tools',
      retrievalStrategy: 'Retrieval Strategy',
      contextTemplate: 'Context Template',
      contextTemplatePlaceholder: 'Custom context template...',
      queryUnderstandModel: 'Модель понимания запроса',
      queryUnderstandModelPlaceholder: 'Оставьте пустым, чтобы использовать основную модель чата',
      rewritePromptSystem: 'Rewrite System Prompt',
      rewritePromptSystemPlaceholder: 'Leave empty to use default prompt',
      rewritePromptUser: 'Rewrite User Prompt',
      rewritePromptUserPlaceholder: 'Leave empty to use default prompt',
      maxCompletionTokens: 'Max Completion Tokens',
      maxCompletionTokensDefault: 'По умолчанию',
      maxCompletionTokensCustom: 'Своё',
      fallbackStrategy: 'Fallback Strategy',
      fallbackResponse: 'Fixed Response',
      fallbackResponsePlaceholder: 'Sorry, I cannot answer this question.',
      fallbackPrompt: 'Fallback Prompt',
      fallbackPromptPlaceholder: 'Leave empty to use default prompt',
      skillsConfig: 'Навыки',
      skillsSelection: 'Список навыков',
      skillsAll: 'Все',
      skillsSelected: 'Выбранные',
      skillsNone: 'Отключено',
      skillsGroupUnavailable: 'Недоступны',
      noSkillsAvailable: 'В каталоге пространства ещё нет навыков.',
      goSandboxSettings: 'Управление песочницами',
      sandboxBackend: 'Песочница',
      memoryEnabled: 'Долговременная память',
      nativeRuntime: {
        adoptRuntime: 'Применить текущие настройки выполнения',
        incompatible: 'Некоторые значения несовместимы с текущей средой. Проверьте изменения ниже. Применение меняет только черновик; изменения вступят в силу после сохранения.',
        adoptQuick: 'Применить текущие настройки быстрых ответов',
        changesPending: 'Изменения применены к черновику и вступят в силу после сохранения.',
        removed: 'Удалить поле',
        defaultsUnavailable: 'Не удалось загрузить текущие настройки выполнения. Загрузите их перед сохранением.',
        retry: 'Загрузить снова',
        resolveBeforeSave: 'Устраните несовместимые настройки перед сохранением.',
        quickDesc: 'Быстрый ответ использует агента для поиска и ответа по мере необходимости с отдельным лимитом вызовов модели.',
        promptDesc: 'Настройте системные инструкции или ссылку на шаблон для текущего режима'
      },
      postCreateHint: {
        title: 'Агент создан',
        footer: 'Продолжите настройку, настройте совместное использование и публикацию, затем нажмите «Сохранить и закрыть».'
      },
      buttons: {
        create: 'Создать агента',
        saveAndClose: 'Сохранить и закрыть'
      }
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
    delete: {
      confirmTitle: 'Delete Agent',
      confirmMessage: 'Are you sure you want to delete agent "{name}"? This action cannot be undone.'
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
    detail: {
      title: 'Agent Details',
      useInChat: 'Use in Chat'
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
    sections: {
      builtin: 'Встроенные',
      mine: 'Созданные мной',
      tenantOthers: 'Рабочая область · Другие участники',
      tenantReadonly: 'Рабочая область · Только просмотр',
      sharedByMe: 'Расшарено мной',
      sharedEditable: 'Доступно мне · Можно редактировать',
      sharedReadonly: 'Доступно мне · Только просмотр'
    },
    tabs: {
      sharedToMe: 'Shared to Me'
    },
    features: {
      webSearch: 'Web Search Enabled',
      knowledgeBase: 'Knowledge Base Linked',
      mcp: 'MCP Services Enabled',
      multiTurn: 'Multi-turn Conversation'
    },
    mode: {
      normal: 'Quick Answer',
      agent: 'Smart Reasoning'
    },
    type: {
      normal: 'Quick Answer',
      agent: 'Smart Reasoning'
    },
    capabilities: {
      kbCount: '{count} knowledge base(s) specified',
      kbAll: 'Access to all knowledge bases',
      mcpEnabled: 'MCP services enabled',
      multiTurn: 'Multi-turn conversation'
    },
    artifactDrawer: {
      buttonTitle: 'Просмотреть файлы, сгенерированные в этом ответе',
      title: 'Сгенерированные файлы',
      empty: 'В этом раунде не создано файлов для скачивания.',
      preview: 'Предпросмотр',
      previewBack: 'Назад к списку',
      collecting: 'Сохранение сгенерированных файлов…',
      delete: 'Удалить',
      deleteTitle: 'Удалить этот файл?',
      deleteConfirm: '«{name}» и сохранённое содержимое будут удалены безвозвратно. Отменить нельзя.',
      deleted: 'Файл удалён',
      deleteFailed: 'Не удалось удалить, повторите попытку.',
      download: 'Скачать',
      downloadFailed: 'Не удалось скачать, повторите попытку.',
      inlinePreviewHint: 'Нажмите для просмотра',
      inlineMissing: 'Файл недоступен',
      inlineDeleted: 'Файл удалён'
    }
  },
  knowledgeStages: {
    expandBranch: 'Expand children',
    collapseBranch: 'Collapse children',
    resizeDrawer: 'Drag to resize panel width',
    status: {
      pending: 'Ожидание',
      running: 'Выполняется',
      finalizing: 'Оптимизация',
      done: 'Готово',
      failed: 'Ошибка',
      skipped: 'Пропущено',
      cancelled: 'Отменено'
    },
    stage: {
      docreader: 'Парсинг документа',
      chunking: 'Разбиение',
      embedding: 'Векторизация',
      multimodal: 'Мультимодальное распознавание',
      postprocess: 'Постобработка'
    },
    stall: {
      title: 'Нет прогресса {minutes} мин.; обработка могла зависнуть'
    },
    processConfig: {
      title: 'Конфигурация обработки'
    }
  },
  uploadConfirm: {
    imageEmbeddingModel: 'Модель эмбеддингов для индексации изображений',
    imageIndexInherited: 'Индексация изображений использует модель эмбеддингов базы знаний. Изменить её можно в настройках базы знаний.',
    imageVectorIndex: 'Индексация изображений для этого импорта',
    imageVectorIndexHint: 'Создавать векторы изображений при этой загрузке или повторном разборе без изменения настроек базы знаний. Поиск по ним по-прежнему зависит от настройки поиска изображений базы знаний.',
    imageVectorRequiresIndex: 'Сначала включите векторную индексацию в настройках базы знаний.',
    documentSummary: 'Сводка документа',
    documentSummaryDescription: 'Выберите, создавать ли сводки документов при этом импорте.',
    generateSummary: 'Создавать сводки документов',
    generateSummaryHint: 'Включено по умолчанию. При отключении создание сводок пропускается, а разбор, индексация и другие этапы выполняются согласно настройкам.',
    title: 'Подтверждение загрузки',
    parseConfig: 'Настройки разбора',
    configNav: 'Навигация по настройкам разбора',
    navParserDefault: 'По умолчанию',
    navParserCustomized: 'Настроено',
    moreOptions: 'Дополнительные параметры обработки',
    summaryParentChildShort: 'Родительско-дочернее',
    summaryParserForceScanned: 'режим скана',
    summaryQuestionCountValue: '{count}',
    summaryGraphTagsValue: '{count}',
    navChunkingSummary: 'Чанк {size}',
    statusOn: 'Вкл.',
    statusOff: 'Выкл.',
    notSet: 'Не задано',
    summaryNoTags: 'Не задано',
    summaryTagsCount: 'Тегов: {count}',
    confirm: 'Загрузить и обработать',
    cancel: 'Отмена',
    tabTags: 'Теги документов',
    tagsDescription: 'Выберите один или несколько тегов для всех документов в этой партии',
    tagsPlaceholder: 'Выберите теги (можно несколько)',
    tagsEmpty: 'В этой базе знаний пока нет тегов. Их можно создать после загрузки.',
    tagsLoadFailed: 'Не удалось загрузить теги. Их можно назначить позже в списке документов.',
    noItems: 'Добавьте хотя бы один файл или URL',
    urlItemLabel: 'URL',
    urlAdded: 'URL добавлен',
    urlDuplicate: 'Этот URL уже в списке',
    statusNeedsSetup: 'Нужна настройка',
    multimodalSetupHint: 'Обнаружены изображения. Включите мультимодальность и выберите модель.',
    asrSetupHint: 'Обнаружено аудио. Включите распознавание речи и выберите модель.',
    vlmModelRequired: 'Настройте мультимодальную модель',
    asrModelRequired: 'Настройте модель распознавания речи',
    vlmModelSelectRequired: 'Мультимодальность включена. Выберите модель VLM.',
    asrModelSelectRequired: 'Распознавание речи включено. Выберите модель ASR.',
    continueAdd: 'Добавить ещё',
    destinationLabel: 'Куда загрузить',
    destinationChange: 'Изменить папку загрузки',
    filesAdded: 'Добавлено файлов: {count}',
    filesAllDuplicate: 'Выбранные файлы уже в списке',
    titleManual: 'Подтверждение публикации',
    confirmManual: 'Опубликовать и обработать',
    titleReparse: 'Подтверждение повторной обработки',
    confirmReparse: 'Подтвердить и обработать заново',
    reparseSource: 'Документ для повторной обработки',
    reparseHint: 'Используются настройки прошлой обработки; их можно изменить здесь',
    manualCharCount: '{count} символов',
    pdfForceScanned: {
      label: 'Разбор PDF как сканированного документа',
      description: 'Подходит для PDF с веб-печати, сканов и документов с большим числом изображений. Каждая страница будет отрендерена в изображение и обработана через OCR/VLM. Может увеличить время обработки и расходы на модели.'
    }
  },
  knowledgeBase: {
    videosFilteredNoVLM: 'Пропущено {count} видеофайлов (загрузка видео не поддерживается)',
    importURL: 'Импорт из URL',
    addDocument: 'Добавить документ',
    importURLTitle: 'Импорт из URL',
    urlRequired: 'Пожалуйста, введите URL',
    invalidURL: 'Пожалуйста, введите корректный URL',
    urlLabel: 'Адрес URL',
    urlPlaceholder: 'Введите URL веб-страницы, например: https://example.com',
    urlTip: 'Поддерживает импорт различного веб-содержимого. Система автоматически извлечет и проанализирует текстовое содержимое с веб-страницы',
    channelLabel: 'Канал источника',
    channelWeb: 'Веб',
    channelApi: 'API',
    channelBrowserExtension: 'Расширение браузера',
    channelWechat: 'WeChat',
    channelWecom: 'WeCom',
    channelFeishu: 'Feishu',
    channelDingtalk: 'DingTalk',
    channelSlack: 'Slack',
    channelIm: 'IM канал',
    channelConfluence: 'Confluence',
    channelGitLab: 'GitLab',
    channelNextcloud: 'Nextcloud',
    channelSeafile: 'Seafile',
    channelIma: 'Tencent IMA',
    channelUnknown: 'Неизвестно',
    selectedCount: 'Выбрано: {count}',
    pdfDocFormat: 'Файлы pdf, doc формата, не более {size} МБ',
    textMarkdownFormat: 'Файлы text, markdown формата, не более {size} МБ',
    dragFileNotText: 'Пожалуйста, перетащите файлы, а не текст или ссылки',
    searchPlaceholder: 'Поиск по базам знаний...',
    noMatch: 'Совпадающих баз знаний не найдено',
    noKnowledge: 'Нет доступных баз знаний',
    loadingFailed: 'Не удалось загрузить базы знаний',
    allFilesSkippedNoEngine: 'Все выбранные файлы были пропущены из-за отсутствия парсера',
    filesSkippedNoEngine: '{count} файл(ов) пропущено из-за отсутствия парсера',
    moveToFolder: {
      action: 'Переместить в папку',
      newFolderPlaceholder: 'Название новой папки',
      newFolderAddRoot: 'Создать подкаталог в корне',
      newFolderAddUnder: 'Создать подкаталог в «{folder}»',
      duplicate: 'Такая папка уже существует'
    },
    folderTree: {
      title: 'Папки',
      rootRow: 'Корень'
    },
    sort: {
      title: 'Сортировка'
    },
    infoCard: {
      title: 'Информация о базе знаний'
    }
  },
  resourceOrigin: {
    mine: 'Мои',
    mineTooltip: 'Создано вами',
    tenant: 'Рабочая область',
    tenantTooltip: 'Создано другим участником рабочей области',
    tenantTooltipWithCreator: 'Создано {creator}',
    space: 'Пространство',
    spaceTooltip: 'Через пространство "{space}"',
    spaceTooltipWithTenant: 'Через пространство "{space}" · от {tenant}',
    shared: 'Внешнее',
    sharedTooltip: 'Доступ из внешнего пространства через общее пространство'
  },
  listSpaceSidebar: {
    all: 'Все',
    workspace: 'Рабочая область',
    spaces: 'Доступно мне',
    favorites: 'Избранное',
    recents: 'Недавние'
  },
  batchManage: {
    selectAll: 'Выбрать все',
    cancel: 'Отмена',
    delete: 'Удалить диалоги',
    deleteConfirmTitle: 'Удалить диалоги',
    deleteConfirmBody: 'Вы уверены, что хотите удалить выбранные {count} диалог(ов)? Это действие необратимо.',
    deleteAllConfirmBody: 'Вы уверены, что хотите удалить все диалоги? Это действие необратимо.',
    deleteSuccess: 'Успешно удалено',
    deleteFailed: 'Ошибка удаления, попробуйте позже'
  },
  contextualGuide: {
    stepOf: '{current} / {total}',
    skip: 'Пропустить',
    prev: 'Назад',
    next: 'Далее',
    done: 'Понятно',
    interactHint: 'Нажмите на выделенную область, чтобы продолжить',
    chat: {
      steps: {
        done: {
          title: 'Можно исследовать',
          desc: 'Задайте вопрос по загруженным документам и посмотрите ответы со ссылками на источники.'
        },
        send: {
          title: 'Отправить, чтобы начать чат',
          desc: 'После отправки создаётся новая сессия. ИИ отвечает на основе базы знаний и показывает цитаты.'
        },
        input: {
          title: 'Введите вопрос',
          desc: 'Опишите, что хотите узнать, или нажмите на рекомендуемый вопрос выше.'
        },
        kb: {
          title: 'Выберите область знаний',
          desc: 'Нажмите {\'@\'}, чтобы выбрать одну или несколько баз знаний или файлов. Иначе используются настройки текущего агента.'
        }
      }
    },
    kbDetail: {
      steps: {
        done: {
          title: 'Готово после индексации',
          desc: 'После обработки документов укажите эту базу через {\'@\'} в чате и получайте ответы со ссылками на источники.'
        },
        upload: {
          title: 'Добавить документы',
          desc: 'Здесь можно загрузить файлы или папки, импортировать URL или создать материал онлайн.'
        },
        intro: {
          title: 'База знаний пуста',
          desc: 'Добавьте первый материал, чтобы искать по нему и общаться в чате. Поддерживаемые файлы можно перетащить мышью.'
        }
      }
    },
    agentCreate: {
      steps: {
        submit: {
          title: 'Сохранить агента',
          desc: 'Нажмите выделенную кнопку подтверждения. Затем выберите этого агента в чате.'
        },
        navTools: {
          title: 'Инструменты и MCP (необязательно)',
          desc: 'В режиме умного рассуждения включите встроенные инструменты и MCP для поиска, кода и др.'
        },
        multimodal: {
          title: 'Включить загрузку вложений',
          desc: 'Настройте загрузку изображений и аудио, а также правила разбора вложений; при загрузке изображений выберите VLM ниже.'
        },
        navMultimodal: {
          title: 'Загрузка вложений (необязательно)',
          desc: 'Позволяет отправлять изображения, документы и аудио в чате; для понимания изображений нужна VLM в настройках.'
        },
        navWebsearch: {
          title: 'Веб-поиск (необязательно)',
          desc: 'Разрешить агенту вызывать внешний поиск для актуальной информации.'
        },
        knowledge: {
          title: 'Область знаний',
          desc: '«Все» — универсальный помощник; «Выбранные» — домен; «Нет» — только модель или веб-поиск.'
        },
        navKnowledge: {
          title: 'Связать базы знаний',
          desc: 'Определите, к каким знаниям агент может обращаться. По умолчанию — все базы.'
        },
        model: {
          title: 'Выбор модели',
          desc: 'Выберите из настроенных моделей чата или сначала добавьте в системных настройках.'
        },
        navModel: {
          title: 'Привязать модель чата',
          desc: 'Каждому агенту нужна модель KnowledgeQA как движок рассуждений.'
        },
        name: {
          title: 'Название и описание',
          desc: 'Укажите узнаваемое имя. В режиме умного рассуждения может подставиться значение по умолчанию.'
        },
        agentType: {
          title: 'Выберите тип агента',
          desc: 'Пресеты подставляют системный промпт, рекомендуемые инструменты и область знаний (например, построение Wiki, анализ данных). При смене типа обновляются имя и описание.'
        },
        mode: {
          title: 'Выберите режим работы',
          desc: '«Быстрый ответ» для простого Q&A; «Умное рассуждение» — инструменты и многошаговое мышление для сложных задач.'
        }
      }
    },
    agentList: {
      steps: {
        create: {
          title: 'Создайте агента',
          desc: 'Агенты объединяют модели, базы знаний, инструменты и промпты в переиспользуемых помощников. Нажмите выделенную кнопку «Создать агента».'
        }
      }
    },
    kbCreate: {
      steps: {
        submit: {
          title: 'Создать базу знаний',
          desc: 'Нажмите «Понятно», чтобы завершить руководство без создания базы знаний. Когда будете готовы, введите название, проверьте тип и модели, затем нажмите «Создать».'
        },
        faq: {
          title: 'Индексация FAQ',
          desc: 'Выберите режим индексации пар вопрос–ответ. Записи FAQ можно добавить после создания.'
        },
        multimodalVllm: {
          title: 'Выберите модель VLM',
          desc: 'Для мультимодальности нужна VLM. Если список пуст, добавьте модель в настройках.'
        },
        multimodalToggle: {
          title: 'Включить мультимодальный разбор',
          desc: 'При включении загрузки с изображениями обрабатываются VLM для лучшего поиска.'
        },
        navMultimodal: {
          title: 'Мультимодальность / изображения (необязательно)',
          desc: 'Включите, если в документах много диаграмм, сканов или изображений, требующих визуального понимания.'
        },
        storage: {
          title: 'Хранилище (необязательно)',
          desc: 'Где хранятся исходные файлы (локально или объектное хранилище). Обычно достаточно значения пространства.'
        },
        chunking: {
          title: 'Разбиение (необязательно)',
          desc: 'Как документ делится на фрагменты для поиска. Размеры по умолчанию подобраны для RAG.'
        },
        parser: {
          title: 'Парсер (необязательно)',
          desc: 'Как разбираются PDF и Office. По умолчанию подходит в большинстве случаев; меняйте при необходимости OCR.'
        },
        embedding: {
          title: 'Модель Embedding',
          desc: 'Преобразует текст в векторы для семантического поиска. Работает с векторным/ключевым индексом выше.'
        },
        llm: {
          title: 'Модель чата / сводки',
          desc: 'Для сводок и ответов. Если список пуст, через выпадающий список откройте настройки и добавьте модель.'
        },
        navModels: {
          title: 'Модели (обязательно)',
          desc: 'Каждой базе нужна модель чата; для поиска также нужен Embedding. Откройте «Конфигурация моделей» слева.'
        },
        indexing: {
          title: 'Возможности индексации',
          desc: 'По умолчанию включены векторный и ключевой поиск. Можно включить Wiki или граф знаний. Оставьте хотя бы один режим поиска.'
        },
        name: {
          title: 'Введите название',
          desc: 'Например «Руководство продукта» или «FAQ поддержки». Описание необязательно.'
        },
        type: {
          title: 'Выберите тип',
          desc: 'Для PDF, Word и похожих файлов — база документов. Для пар вопрос–ответ — база FAQ. Тип после создания изменить нельзя.'
        }
      }
    },
    tenantModels: {
      needChatModelFirst: 'Перед созданием агента добавьте модель чата (KnowledgeQA).',
      stepsAgent: {
        done: {
          title: 'Затем создайте агента',
          desc: 'После сохранения закройте настройки и нажмите «Создать агента». Мастер охватит режим, базы знаний и загрузку вложений.'
        },
        addModel: {
          title: 'Добавить модель чата',
          desc: 'Нажмите «Добавить модель» и настройте тип KnowledgeQA.'
        },
        intro: {
          title: 'Сначала настройте модель чата',
          desc: 'Для создания агента нужна хотя бы одна модель KnowledgeQA. Добавьте её в системных настройках (Embedding нужен только для баз знаний).'
        }
      },
      steps: {
        done: {
          title: 'Затем продолжите',
          desc: 'После сохранения моделей закройте настройки и нажмите «Новая база знаний». Мастер проведёт через тип, индексацию и привязку моделей.'
        },
        addModel: {
          title: 'Добавить модели',
          desc: 'Нажмите «Добавить модель» и настройте типы KnowledgeQA (чат) и Embedding. В Lite можно загрузить локальные модели через Ollama.'
        },
        intro: {
          title: 'Сначала настройте модели',
          desc: 'Для документной базы нужна модель чата (сводки и ответы) и модель Embedding (векторный поиск). Добавьте их в системных настройках.'
        }
      }
    },
    kbList: {
      steps: {
        create: {
          title: 'Создайте первую базу знаний',
          desc: 'В базах знаний хранятся документы и FAQ. Нажмите выделенную кнопку «Новая база знаний» ниже — мы проведём вас по форме.'
        }
      }
    }
  },
  newUserGuide: {
    stepOf: '{current} / {total}',
    skip: 'Пропустить',
    prev: 'Назад',
    next: 'Далее',
    done: 'Готово',
    reopen: 'Обучение',
    steps: {
      done: {
        title: 'Всё готово',
        desc: 'Теперь вы знаете основы — начните создавать своего помощника на основе знаний! Вернуться к обучению можно кнопкой помощи рядом с именем в этом меню.'
      },
      models: {
        title: 'Настройте модели',
        desc: 'Ключевой шаг: добавьте модели чата, эмбеддингов и другие в управлении моделями, чтобы базы знаний и чат работали. Нажмите «Добавить модель», чтобы начать.'
      },
      settings: {
        title: 'Аккаунт и настройки',
        desc: 'Откройте это меню, чтобы управлять аккаунтом, участниками и системными настройками. Обучение можно снова открыть кнопкой помощи рядом с именем вверху меню.'
      },
      agents: {
        title: 'Создавайте собственных агентов',
        desc: 'Объединяйте базы знаний, промпты и инструменты в переиспользуемых агентов, закрепляя свою экспертизу.'
      },
      chat: {
        title: 'Начните чат с ИИ',
        desc: 'Задавайте вопросы на основе вашей базы знаний и получайте точные ответы со ссылками на источники. Нажмите здесь, чтобы начать новый чат.'
      },
      knowledge: {
        title: 'Создайте базу знаний',
        desc: 'С этого всё начинается: загружайте документы, веб-страницы или FAQ, и Xiaozhi автоматически разберёт и проиндексирует их. Нажмите здесь, чтобы открыть базы знаний.'
      },
      welcome: {
        title: 'Добро пожаловать в Xiaozhi',
        desc: 'Несколько простых шагов познакомят вас с базами знаний, чатом и агентами. Нажмите «Далее», чтобы начать.'
      },
      assistant: {
        title: 'Знакомьтесь: помощник Xiaozhi',
        desc: 'Задавайте вопросы о версиях, функциях и настройке Xiaozhi. Учитывая текущую страницу, помощник может создавать агентов, планировать задачи и упорядочивать знания от вашего имени, в пределах ваших прав.'
      }
    }
  },
  assistantEntryGuide: {
    stepOf: 'НОВОЕ В v0.9.0',
    skip: 'Понятно',
    interactHint: 'Нажмите выделенную кнопку, чтобы открыть помощника.'
  },
  chatHeader: {
    automationTask: 'Автоматизация',
    moreActions: 'Другие действия с диалогом',
    toggleSandboxPanel: 'Терминал песочницы',
    copyMarkdown: 'Копировать как Markdown',
    deleteSession: 'Удалить диалог',
    renamePlaceholder: 'Введите название диалога',
    temporaryWorkspace: 'Временная рабочая область',
    markdownCopied: 'Весь диалог скопирован как Markdown',
    markdownCopyFailed: 'Не удалось скопировать Markdown. Повторите попытку.',
    clearConfirmTitle: 'Очистить сообщения диалога',
    clearConfirmBody: 'Очистить все сообщения? Диалог останется, но это действие нельзя отменить.',
    deleteConfirmTitle: 'Удалить диалог',
    deleteConfirmBody: 'Удалить этот диалог? Это действие нельзя отменить.',
    deleteSuccess: 'Диалог удалён',
    markdown: {
      sessionId: 'ID сессии',
      exportedAt: 'Время экспорта',
      user: 'Пользователь',
      assistant: 'Ассистент',
      attachments: 'Вложения',
      references: 'Источники'
    },
    grants: {
      menu: 'Разрешённые действия',
      description: 'Действия, разрешённые в этом диалоге без повторного запроса. После отзыва запрос появится снова.',
      empty: 'Разрешённых действий пока нет',
      revoke: 'Отозвать',
      revoked: 'Отозвано',
      revokeFailed: 'Не удалось отозвать',
      loadFailed: 'Не удалось загрузить'
    }
  },
  menu: {
    sessionInProgress: 'Диалог выполняется',
    sessionUnread: 'Новый ответ',
    knowledgeBase: 'База знаний',
    agents: 'Агенты',
    automations: 'Автоматизации',
    artifacts: 'Артефакты',
    organizations: 'Общие пространства',
    newChat: 'Новый диалог',
    settings: 'Настройки системы',
    logout: 'Выход',
    clearMessages: 'Очистить сообщения',
    clearMessagesSuccess: 'Сообщения очищены',
    clearMessagesFailed: 'Не удалось очистить сообщения, попробуйте позже',
    renameSession: 'Переименовать',
    renameSessionSuccess: 'Название обновлено',
    renameSessionFailed: 'Не удалось обновить название, попробуйте позже',
    batchManage: 'Пакетное управление',
    newSession: 'Новый диалог',
    pin: 'Закрепить',
    unpin: 'Открепить',
    pinFailed: 'Не удалось закрепить, попробуйте позже',
    unpinFailed: 'Не удалось открепить, попробуйте позже',
    search: 'Поиск',
    collapseSidebar: 'Свернуть боковую панель',
    expandSidebar: 'Развернуть боковую панель',
    myChats: 'Мои чаты',
    apiChats: 'Сессии API',
    noSessions: 'Пока нет диалогов'
  },
  resourceSort: {
    title: 'Сортировка',
    updatedTime: 'Время обновления',
    updatedTimeDescription: 'Вариант по умолчанию.',
    createdTime: 'Время создания',
    createdTimeDescription: 'Показать недавно или давно созданные элементы',
    name: 'Название',
    nameDescription: 'Быстро найти элемент по известному названию',
    recentlyUpdated: 'Сначала обновлённые',
    earliestUpdated: 'Сначала давно обновлённые',
    recentlyCreated: 'Сначала новые',
    earliestCreated: 'Сначала старые',
    nameAscending: 'A–Z',
    nameDescending: 'Z–A'
  },
  artifactLibrary: {
    title: 'Артефакты',
    subtitle: 'Файлы, созданные агентами во всех ваших диалогах',
    typeFilter: 'Фильтр по типу',
    searchPlaceholder: 'Поиск по имени файла',
    total: 'Файлов: {count}',
    versions: 'Версий: {count}',
    preview: 'Предпросмотр',
    delete: 'Удалить',
    deleteTitle: 'Удалить этот файл?',
    deleteConfirm: '«{name}» и сохранённое содержимое будут удалены безвозвратно. Отменить нельзя.',
    deleteConfirmVersions: 'Все версии файла «{name}» ({count}) и их содержимое будут удалены безвозвратно. Отменить нельзя.',
    deleted: 'Файл удалён',
    deleteFailed: 'Не удалось удалить, повторите попытку.',
    download: 'Скачать',
    downloadFailed: 'Не удалось скачать файл. Повторите попытку позже',
    openSession: 'Открыть диалог',
    untitledSession: 'Диалог без названия',
    loadMore: 'Загрузить ещё',
    loadFailed: 'Не удалось загрузить артефакты',
    retry: 'Повторить',
    clearFilters: 'Сбросить фильтры',
    noMatches: {
      title: 'Нет подходящих файлов',
      description: 'Попробуйте другое ключевое слово или тип файла'
    },
    empty: {
      title: 'Артефактов пока нет',
      description: 'Попросите агента подготовить отчёт, таблицу или презентацию — файлы появятся здесь'
    },
    groups: {
      today: 'Сегодня',
      yesterday: 'Вчера',
      last7Days: 'Последние 7 дней',
      last30Days: 'Последние 30 дней',
      earlier: 'Ранее'
    },
    categories: {
      all: 'Все',
      document: 'Документы',
      spreadsheet: 'Таблицы',
      presentation: 'Презентации',
      image: 'Изображения',
      web: 'Веб-страницы',
      data: 'Данные'
    }
  },
  localBrowser: {
    pipOpen: 'Открыть плавающее окно',
    pipReturn: 'Вернуть предпросмотр в чат',
    pipFailed: 'Не удалось открыть плавающее окно. Повторите попытку.',
    captureScreenshot: 'Сделать снимок страницы',
    navigationIncomplete: 'Страница не достигла нужного этапа загрузки. Проверьте её состояние.',
    noEntries: 'Записи отсутствуют.',
    stopping: 'Завершение задачи…',
    elapsedSeconds: '{seconds} с',
    searchInstructionsTitle: 'Инструкции поиска в браузере',
    searchInstructionsDescription: 'Укажите предпочитаемую поисковую систему и URL поиска.',
    searchInstructionsHint: 'Применяется со следующего запроса. Пустое поле — настройки по умолчанию.',
    searchInstructionsReset: 'Восстановить по умолчанию',
    searchInstructionsSaved: 'Сохранено',
    sourceHint: 'Использовать локальный браузер для просмотра страниц и работы с ними в этом запросе совместно с веб-поиском, базами знаний и другими инструментами.',
    pressKey: 'Нажать клавишу',
    hoverPage: 'Навести на элемент',
    scrollPage: 'Прокрутить страницу',
    focusElement: 'Сфокусировать элемент',
    blurElement: 'Убрать фокус',
    selectOption: 'Выбрать вариант',
    closeTab: 'Закрыть вкладку',
    runScript: 'Выполнить скрипт страницы',
    readConsole: 'Просмотреть консоль',
    readNetwork: 'Просмотреть сетевые запросы',
    resizeWindow: 'Изменить размер окна',
    emulateDevice: 'Эмулировать устройство',
    actionPending: 'Управление браузером…',
    actionRecorded: 'Действие браузера записано',
    untitledTab: 'Вкладка без названия',
    contentTruncated: 'Показана только часть содержимого страницы.',
    controlScope: 'Управление браузером только этого диалога',
    pauseHint: 'Прервать действие браузера, сохранив страницы для продолжения. Диалог не останавливается.',
    stopHint: 'Закрыть вкладки этой задачи и вернуть заимствованные. Браузер и сопряжение сохраняются.',
    openPage: 'Открыть страницу',
    switchPage: 'Переключить страницу',
    readPage: 'Просмотреть страницу',
    listTabs: 'Список вкладок',
    clickPage: 'Нажать на элемент',
    fillPage: 'Ввести данные',
    waitPage: 'Ожидать страницу',
    openTab: 'Создать вкладку задачи',
    switchTab: 'Переключить вкладку задачи',
    authorizeTab: 'Запросить доступ',
    returnTab: 'Вернуть вкладку',
    needHelp: 'Нужен ваш ввод',
    browserAction: 'Действие браузера',
    actionFailed: 'Не завершено',
    actionCompleted: 'Действие завершено',
    commandBusy: 'Предыдущая команда ещё выполняется. Дождитесь завершения.',
    invalidArguments: 'Аргументы инструмента браузера неверны или неполны. Агент должен исправить их перед выполнением.',
    commandInterrupted: 'Действие прервано. Проверьте страницу перед продолжением через предпросмотр.',
    actionFailedHint: 'Действие браузера не завершено. Проверьте страницу и повторите попытку.',
    previewStale: 'Изображение не обновлено',
    previewIdle: 'Сохранено последнее изображение',
    previewLive: 'Изображение обновляется',
    previewLoading: 'Получение изображения',
    borrowHint: 'Перейдите на запрашиваемую вкладку и выберите «Разрешить» или «Отклонить» в окне BrowserSkill. После разрешения работа продолжится автоматически. Продолжение приостановленной задачи не даёт разрешения на доступ к вкладке.',
    helpHint: 'Требуется проверка или разрешение. Нажмите предпросмотр для перехода.',
    settingsTitle: 'Подключение браузера',
    settingsDescription: 'Подключите локальный Chrome или Edge через BrowserSkill, чтобы управлять реальными страницами из диалогов.',
    openSettings: 'Открыть настройки',
    settingsHint: 'Подключите BrowserSkill в разделе «Инструменты», чтобы использовать локальный браузер.',
    unavailable: 'Локальный браузер не включён на сервере. Обратитесь к администратору.',
    source: 'Источник браузера',
    sandbox: 'Браузер песочницы',
    local: 'Локальный браузер',
    paused: 'Приостановлено',
    connected: 'Подключено',
    disconnected: 'Не подключено',
    resume: 'Продолжить в браузере',
    pause: 'Приостановить браузер',
    start: 'Начать задачу',
    stop: 'Завершить задачу браузера',
    resumeShort: 'Продолжить',
    pauseShort: 'Пауза',
    stopShort: 'Завершить',
    pairHint: 'Откройте в расширении «Настройки подключения → Удалённое подключение», вставьте ссылку и подтвердите сервер. Ссылка действует 5 минут и используется один раз.',
    copyPairing: 'Скопировать ссылку',
    copied: 'Скопировано',
    windowHint: 'Задачи выполняются в отдельном окне браузера. Заимствование существующих вкладок требует вашего разрешения.',
    preview: 'Предпросмотр локального браузера',
    waiting: 'Ожидание страницы задачи',
    startHint: 'Запрос к браузеру создаёт отдельное окно агента.',
    revoke: 'Отозвать доступ устройства',
    revokeConfirm: 'После отзыва потребуется повторное подключение, чтобы снова использовать локальный браузер.',
    failed: 'Операция не удалась. Повторите попытку.',
    productDescription: 'Расширение Chrome и Edge с открытым исходным кодом: агент открывает страницы, читает их и выполняет действия в вашем браузере.',
    offline: 'Не в сети',
    notPaired: 'Не подключён',
    lastSeen: 'Последнее подключение',
    readyHint: 'Готово. Вернитесь в диалог и опишите задачу для браузера.',
    capabilitiesTitle: 'Агент может',
    sidebarStatus: 'Показывать статус подключения на боковой панели',
    reconnectHint: 'Авторизация сохранена. Откройте браузер и BrowserSkill для автоматического подключения.',
    replaceDevice: 'Сменить браузер',
    installExtension: 'Установите BrowserSkill',
    storeInstall: 'Интернет-магазин Chrome',
    edgeStoreInstall: 'Надстройки Edge',
    extensionMinVersion: 'Требуется BrowserSkill v{version} или новее. Поддерживаются Chrome и Edge.',
    extensionOutdated: 'Версия расширения v{current} устарела. Обновите до v{version} или новее.',
    manualInstall: 'Установить вручную (альтернатива)',
    storeInstallHint: 'Установите BrowserSkill из Интернет-магазина Chrome или надстроек Edge, затем вернитесь сюда для сопряжения.',
    installHint: 'Если магазин недоступен или версия несовместима, скачайте подходящий пакет и установите его вручную.',
    downloadExtension: 'Скачать совместимый пакет',
    officialExtension: 'Официальное расширение (Интернет-магазин Chrome)',
    installGuide: 'Как установить скачанный пакет?',
    pairGuide: 'Как использовать ссылку сопряжения?',
    pairBrowser: 'Подключите браузер',
    packageUnavailable: 'Запросите совместимое расширение у администратора.',
    manualCopy: 'Скопируйте ссылку ниже. Она действует 5 минут и используется один раз.',
    pairingReady: 'Ссылка скопирована. Вставьте её в расширение в течение 5 минут. Используется один раз.',
    copyAgain: 'Копировать ещё раз',
    usageTitle: 'Как пользоваться',
    usageStep1Title: 'Установите расширение',
    usageStep1Text: 'Распакуйте ZIP, введите chrome://extensions (в Edge — edge://extensions) в адресной строке, включите режим разработчика, нажмите «Загрузить распакованное расширение» и выберите папку расширения.',
    usageStep2Title: 'Подключите браузер',
    usageStep2Text: 'Вставьте ссылку в «Настройки подключения → Удалённое подключение» расширения и подтвердите сервер. Одно подключение используется во всех диалогах пространства.',
    usageStep3Title: 'Опишите задачу в диалоге',
    usageStep3Text: 'Перед отправкой веб-задачи включите локальный браузер в поле ввода диалога. Подключение не включает эту опцию автоматически. Задачи выполняются в отдельном окне агента.',
    usageStep4Title: 'Просматривайте и продолжайте через предпросмотр',
    usageStep4Text: 'В диалоге появится миниатюра. Нажмите её, чтобы перейти к вкладке задачи. Прерванные задачи остаются на паузе после переподключения — продолжите через предпросмотр. Для существующих вкладок нужно разрешение.',
    running: 'Выполняется',
    locateWindow: 'Показать браузер',
    reconnectShort: 'Ожидание подключения'
  },
  toolbox: {
    title: 'Инструменты',
    unavailable: 'В текущем рабочем пространстве нет доступных инструментов.'
  },
  automation: {
    conversationNotice: 'Этот диалог выполняется автоматизацией. Отправка сообщений вручную недоступна. Обработайте ожидающие запросы выше.'
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
