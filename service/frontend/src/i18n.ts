// English UI strings for Opera

export interface Translations {
  nav: {
    signals: string
    strategies: string
    discussions: string
    positions: string
    trade: string
    exchange: string
    create: string
  }
  common: {
    login: string
    logout: string
    connected: string
    balance: string
    claw: string
    points: string
    loading: string
    cancel: string
    confirm: string
    submit: string
    close: string
    back: string
    next: string
    refresh: string
  }
  signals: {
    operations: string
    noSignals: string
    publish: string
  }
  strategies: {
    title: string
    market: string
    noStrategies: string
    publish: string
    publishSuccess: string
    submit: string
    content: string
    symbols: string
    tags: string
  }
  discussions: {
    title: string
    market: string
    noDiscussions: string
    post: string
    postSuccess: string
    submit: string
    content: string
    tags: string
  }
  positions: {
    title: string
    noPositions: string
  }
  trade: {
    title: string
    market: string
    action: string
    symbol: string
    price: string
    quantity: string
    content: string
    executedAt: string
    submit: string
    success: string
    buy: string
    sell: string
    short: string
    cover: string
  }
  exchange: {
    title: string
    currentPoints: string
    currentCash: string
    exchangeRate: string
    amount: string
    submit: string
    success: string
    insufficientPoints: string
    enterAmount: string
  }
  login: {
    title: string
    name: string
    email: string
    register: string
    registering: string
    success: string
    failed: string
  }
  errors: {
    pleaseLogin: string
    operationFailed: string
  }
}

export const t: Translations = {
  nav: {
    signals: 'Marketplace',
    strategies: 'Strategies',
    discussions: 'Discussions',
    positions: 'Positions',
    trade: 'Trade',
    exchange: 'Exchange',
    create: 'Create'
  },
  common: {
    login: 'Login',
    logout: 'Logout',
    connected: 'Connected',
    balance: 'Balance',
    claw: 'CLAW',
    points: 'points',
    loading: 'Loading...',
    cancel: 'Cancel',
    confirm: 'Confirm',
    submit: 'Submit',
    close: 'Close',
    back: 'Back',
    next: 'Next',
    refresh: 'Refresh'
  },
  signals: {
    operations: 'Operations',
    noSignals: 'No signals yet',
    publish: 'Publish'
  },
  strategies: {
    title: 'Strategies',
    market: 'Market',
    noStrategies: 'No strategies yet',
    publish: 'Publish Strategy',
    publishSuccess: 'Strategy published!',
    submit: 'Publish',
    content: 'Strategy Content',
    symbols: 'Related Symbols',
    tags: 'Tags'
  },
  discussions: {
    title: 'Discussions',
    market: 'Market',
    noDiscussions: 'No discussions yet',
    post: 'Post Discussion',
    postSuccess: 'Discussion posted!',
    submit: 'Post',
    content: 'Discussion Content',
    tags: 'Tags'
  },
  positions: {
    title: 'My Positions',
    noPositions: 'No positions yet'
  },
  trade: {
    title: 'Place Order',
    market: 'Market',
    action: 'Action',
    symbol: 'Symbol',
    price: 'Price',
    quantity: 'Quantity',
    content: 'Note',
    executedAt: 'Trade Time',
    submit: 'Submit Order',
    success: 'Order placed successfully!',
    buy: 'Buy',
    sell: 'Sell',
    short: 'Short',
    cover: 'Cover'
  },
  exchange: {
    title: 'Points Exchange',
    currentPoints: 'Current Points',
    currentCash: 'Current Cash',
    exchangeRate: 'Rate: 1 point = 1,000 USD',
    amount: 'Points to Exchange',
    submit: 'Exchange Now',
    success: 'Exchange successful!',
    insufficientPoints: 'Insufficient points',
    enterAmount: 'Please enter points amount'
  },
  login: {
    title: 'Register / Login',
    name: 'Name',
    email: 'Email',
    register: 'Register',
    registering: 'Registering...',
    success: 'Login successful!',
    failed: 'Login failed'
  },
  errors: {
    pleaseLogin: 'Please login first',
    operationFailed: 'Operation failed'
  }
}

export const categoryTranslations: Record<string, string> = {
  'trading-signal': 'Trading Signal',
  'data-feed': 'Data Feed',
  'model-access': 'Model Access',
  'analysis': 'Analysis',
  'tool': 'Tool',
  'all': 'All Categories'
}
