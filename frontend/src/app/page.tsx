import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Music, PenTool, Database, Sparkles } from 'lucide-react'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-purple-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Music className="h-8 w-8 text-purple-600" />
            <span className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              he_write
            </span>
          </div>
          <nav className="flex gap-4">
            <Link href="/lyricists">
              <Button variant="ghost">作词人</Button>
            </Link>
            <Link href="/samples">
              <Button variant="ghost">样本库</Button>
            </Link>
            <Link href="/models">
              <Button variant="ghost">模型训练</Button>
            </Link>
            <Link href="/generate">
              <Button>开始创作</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 bg-clip-text text-transparent">
          AI 作词人训练系统
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
          采集你喜爱的作词人作品，训练专属风格模型，生成独特风格的歌词
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/lyricists">
            <Button size="lg" className="gap-2">
              <Sparkles className="h-5 w-5" />
              开始使用
            </Button>
          </Link>
          <Link href="/docs">
            <Button size="lg" variant="outline">
              查看文档
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">核心功能</h2>
        <div className="grid md:grid-cols-4 gap-8">
          <div className="p-6 rounded-xl bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow">
            <div className="h-12 w-12 rounded-lg bg-purple-100 dark:bg-purple-900 flex items-center justify-center mb-4">
              <Database className="h-6 w-6 text-purple-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">作词人信息采集</h3>
            <p className="text-gray-600 dark:text-gray-400">
              自动从多个音乐平台爬取作词人作品，智能清洗去重
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow">
            <div className="h-12 w-12 rounded-lg bg-pink-100 dark:bg-pink-900 flex items-center justify-center mb-4">
              <PenTool className="h-6 w-6 text-pink-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">样本库管理</h3>
            <p className="text-gray-600 dark:text-gray-400">
              手动添加编辑歌词，分类管理，质量评估筛选
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow">
            <div className="h-12 w-12 rounded-lg bg-orange-100 dark:bg-orange-900 flex items-center justify-center mb-4">
              <Music className="h-6 w-6 text-orange-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">模型训练</h3>
            <p className="text-gray-600 dark:text-gray-400">
              基于 GPT-2 训练专属风格模型，实时监控训练进度
            </p>
          </div>

          <div className="p-6 rounded-xl bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow">
            <div className="h-12 w-12 rounded-lg bg-green-100 dark:bg-green-900 flex items-center justify-center mb-4">
              <Sparkles className="h-6 w-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold mb-2">歌词生成</h3>
            <p className="text-gray-600 dark:text-gray-400">
              输入关键词或主题，生成特定作词人风格的歌词
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-2xl p-8 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">准备好创作了吗？</h2>
          <p className="text-lg mb-6 opacity-90">
            选择你喜爱的作词人，开始训练专属模型
          </p>
          <Link href="/lyricists">
            <Button size="lg" variant="secondary" className="gap-2">
              立即开始
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-gray-600 dark:text-gray-400">
          <p>© 2024 he_write. AI 作词人训练系统</p>
        </div>
      </footer>
    </main>
  )
}
