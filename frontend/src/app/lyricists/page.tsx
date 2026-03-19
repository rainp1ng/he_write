'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { 
  Plus, Search, Edit2, Trash2, Music, FolderOpen, 
  MoreVertical, User 
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { lyricistApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

interface Lyricist {
  id: number
  name: string
  alias?: string
  style?: string
  description?: string
  sample_count: number
  model_count: number
  created_at: string
  updated_at: string
}

export default function LyricistsPage() {
  const [search, setSearch] = useState('')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [editingLyricist, setEditingLyricist] = useState<Lyricist | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    alias: '',
    style: '',
    description: '',
  })
  
  const queryClient = useQueryClient()
  const { toast } = useToast()

  // 获取作词人列表
  const { data: lyricists, isLoading } = useQuery({
    queryKey: ['lyricists', search],
    queryFn: async () => {
      const res = await lyricistApi.list({ search: search || undefined })
      return res.data as Lyricist[]
    },
  })

  // 创建作词人
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => lyricistApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lyricists'] })
      setIsCreateOpen(false)
      resetForm()
      toast({ title: '创建成功' })
    },
    onError: (error: any) => {
      toast({ 
        title: '创建失败', 
        description: error.response?.data?.detail || '未知错误',
        variant: 'destructive'
      })
    },
  })

  // 更新作词人
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: typeof formData }) =>
      lyricistApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lyricists'] })
      setEditingLyricist(null)
      resetForm()
      toast({ title: '更新成功' })
    },
    onError: (error: any) => {
      toast({ 
        title: '更新失败', 
        description: error.response?.data?.detail || '未知错误',
        variant: 'destructive'
      })
    },
  })

  // 删除作词人
  const deleteMutation = useMutation({
    mutationFn: (id: number) => lyricistApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lyricists'] })
      toast({ title: '删除成功' })
    },
    onError: (error: any) => {
      toast({ 
        title: '删除失败', 
        description: error.response?.data?.detail || '未知错误',
        variant: 'destructive'
      })
    },
  })

  const resetForm = () => {
    setFormData({ name: '', alias: '', style: '', description: '' })
  }

  const handleSubmit = () => {
    if (!formData.name.trim()) {
      toast({ title: '请输入作词人姓名', variant: 'destructive' })
      return
    }
    
    if (editingLyricist) {
      updateMutation.mutate({ id: editingLyricist.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const openEdit = (lyricist: Lyricist) => {
    setEditingLyricist(lyricist)
    setFormData({
      name: lyricist.name,
      alias: lyricist.alias || '',
      style: lyricist.style || '',
      description: lyricist.description || '',
    })
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2">
                <Music className="h-6 w-6 text-purple-600" />
                <span className="text-xl font-bold">he_write</span>
              </Link>
              <span className="text-gray-400">/</span>
              <h1 className="text-lg font-semibold">作词人管理</h1>
            </div>
            <nav className="flex gap-2">
              <Link href="/samples">
                <Button variant="ghost" size="sm">样本库</Button>
              </Link>
              <Link href="/models">
                <Button variant="ghost" size="sm">模型训练</Button>
              </Link>
              <Link href="/generate">
                <Button size="sm">开始创作</Button>
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="搜索作词人..."
              className="pl-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            添加作词人
          </Button>
        </div>

        {/* List */}
        {isLoading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : lyricists?.length === 0 ? (
          <div className="text-center py-12">
            <User className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">暂无作词人，点击上方按钮添加</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lyricists?.map((lyricist) => (
              <Card key={lyricist.id} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{lyricist.name}</CardTitle>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEdit(lyricist)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          if (confirm('确定要删除该作词人吗？')) {
                            deleteMutation.mutate(lyricist.id)
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                  {lyricist.alias && (
                    <p className="text-sm text-gray-500">别名：{lyricist.alias}</p>
                  )}
                </CardHeader>
                <CardContent>
                  {lyricist.style && (
                    <p className="text-sm text-gray-600 mb-2">
                      <span className="font-medium">风格：</span>
                      {lyricist.style}
                    </p>
                  )}
                  {lyricist.description && (
                    <p className="text-sm text-gray-500 line-clamp-2 mb-3">
                      {lyricist.description}
                    </p>
                  )}
                  <div className="flex gap-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <FolderOpen className="h-4 w-4" />
                      {lyricist.sample_count} 样本
                    </span>
                    <span className="flex items-center gap-1">
                      <Music className="h-4 w-4" />
                      {lyricist.model_count} 模型
                    </span>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Link href={`/samples?lyricist_id=${lyricist.id}`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        查看样本
                      </Button>
                    </Link>
                    <Link href={`/models?lyricist_id=${lyricist.id}`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        训练模型
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateOpen || !!editingLyricist} onOpenChange={(open) => {
        if (!open) {
          setIsCreateOpen(false)
          setEditingLyricist(null)
          resetForm()
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingLyricist ? '编辑作词人' : '添加作词人'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">姓名 *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="作词人姓名"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="alias">别名</Label>
              <Input
                id="alias"
                value={formData.alias}
                onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                placeholder="别名/艺名"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="style">风格</Label>
              <Input
                id="style"
                value={formData.style}
                onChange={(e) => setFormData({ ...formData, style: e.target.value })}
                placeholder="如：流行、摇滚、民谣"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="作词人简介..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsCreateOpen(false)
              setEditingLyricist(null)
              resetForm()
            }}>
              取消
            </Button>
            <Button 
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  )
}
