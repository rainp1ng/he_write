'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { 
  Plus, Search, Edit2, Trash2, Music, FileText, Upload,
  Check, X, Clock, Eye
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
import { sampleApi, lyricistApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

interface Sample {
  id: number
  lyricist_id: number
  lyricist_name?: string
  title?: string
  content: string
  source?: string
  status: string
  quality_score?: number
  tags?: string[]
  created_at: string
}

interface Lyricist {
  id: number
  name: string
}

export default function SamplesPage() {
  const searchParams = useSearchParams()
  const initialLyricistId = searchParams.get('lyricist_id')
  
  const [search, setSearch] = useState('')
  const [selectedLyricistId, setSelectedLyricistId] = useState<number | null>(
    initialLyricistId ? Number(initialLyricistId) : null
  )
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [viewingSample, setViewingSample] = useState<Sample | null>(null)
  const [editingSample, setEditingSample] = useState<Sample | null>(null)
  const [formData, setFormData] = useState({
    lyricist_id: 0,
    title: '',
    content: '',
    source: '',
    tags: [] as string[],
  })
  const [tagInput, setTagInput] = useState('')
  
  const queryClient = useQueryClient()
  const { toast } = useToast()

  // 获取样本列表
  const { data: samples, isLoading } = useQuery({
    queryKey: ['samples', search, selectedLyricistId, statusFilter],
    queryFn: async () => {
      const res = await sampleApi.list({ 
        search: search || undefined,
        lyricist_id: selectedLyricistId || undefined,
        status: statusFilter || undefined
      })
      return res.data as Sample[]
    },
  })

  // 获取作词人列表
  const { data: lyricists } = useQuery({
    queryKey: ['lyricists'],
    queryFn: async () => {
      const res = await lyricistApi.list({ limit: 100 })
      return res.data as Lyricist[]
    },
  })

  // 创建样本
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => sampleApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['samples'] })
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

  // 更新样本
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => sampleApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['samples'] })
      setEditingSample(null)
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

  // 删除样本
  const deleteMutation = useMutation({
    mutationFn: (id: number) => sampleApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['samples'] })
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

  // 审核样本
  const approveMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      sampleApi.update(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['samples'] })
      toast({ title: '状态已更新' })
    },
  })

  const resetForm = () => {
    setFormData({
      lyricist_id: 0,
      title: '',
      content: '',
      source: '',
      tags: [],
    })
    setTagInput('')
  }

  const handleSubmit = () => {
    if (!formData.content.trim()) {
      toast({ title: '请输入歌词内容', variant: 'destructive' })
      return
    }
    
    const lyricistId = formData.lyricist_id || selectedLyricistId || lyricists?.[0]?.id
    if (!lyricistId) {
      toast({ title: '请选择作词人', variant: 'destructive' })
      return
    }
    
    const data = { ...formData, lyricist_id: lyricistId }
    
    if (editingSample) {
      updateMutation.mutate({ id: editingSample.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const openEdit = (sample: Sample) => {
    setEditingSample(sample)
    setFormData({
      lyricist_id: sample.lyricist_id,
      title: sample.title || '',
      content: sample.content,
      source: sample.source || '',
      tags: sample.tags || [],
    })
  }

  const addTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData({ ...formData, tags: [...formData.tags, tagInput.trim()] })
      setTagInput('')
    }
  }

  const removeTag = (tag: string) => {
    setFormData({ ...formData, tags: formData.tags.filter(t => t !== tag) })
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, { bg: string; text: string }> = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-600' },
      approved: { bg: 'bg-green-100', text: 'text-green-600' },
      rejected: { bg: 'bg-red-100', text: 'text-red-600' },
    }
    
    const style = styles[status] || styles.pending
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${style.bg} ${style.text}`}>
        {status === 'approved' ? '已审核' : status === 'rejected' ? '已拒绝' : '待审核'}
      </span>
    )
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
              <h1 className="text-lg font-semibold">样本库管理</h1>
            </div>
            <nav className="flex gap-2">
              <Link href="/lyricists">
                <Button variant="ghost" size="sm">作词人</Button>
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
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="搜索歌词..."
              className="pl-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="px-3 py-2 border rounded-md bg-white dark:bg-gray-800"
            value={selectedLyricistId || ''}
            onChange={(e) => setSelectedLyricistId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">全部作词人</option>
            {lyricists?.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
          <select
            className="px-3 py-2 border rounded-md bg-white dark:bg-gray-800"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">全部状态</option>
            <option value="pending">待审核</option>
            <option value="approved">已审核</option>
            <option value="rejected">已拒绝</option>
          </select>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            添加样本
          </Button>
        </div>

        {/* Samples List */}
        {isLoading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : samples?.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">暂无歌词样本，点击上方按钮添加</p>
          </div>
        ) : (
          <div className="space-y-4">
            {samples?.map((sample) => (
              <Card key={sample.id} className="hover:shadow-md transition-shadow">
                <CardContent className="py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-medium truncate">
                          {sample.title || '无标题'}
                        </h3>
                        {getStatusBadge(sample.status)}
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        作词人：{sample.lyricist_name || '-'} 
                        {sample.source && <span className="ml-2">来源：{sample.source}</span>}
                      </p>
                      <p className="text-sm text-gray-500 line-clamp-2">
                        {sample.content.substring(0, 200)}...
                      </p>
                      {sample.tags && sample.tags.length > 0 && (
                        <div className="flex gap-1 mt-2">
                          {sample.tags.map((tag) => (
                            <span key={tag} className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setViewingSample(sample)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      {sample.status === 'pending' && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => approveMutation.mutate({ id: sample.id, status: 'approved' })}
                          >
                            <Check className="h-4 w-4 text-green-500" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => approveMutation.mutate({ id: sample.id, status: 'rejected' })}
                          >
                            <X className="h-4 w-4 text-red-500" />
                          </Button>
                        </>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEdit(sample)}
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm('确定要删除该样本吗？')) {
                            deleteMutation.mutate(sample.id)
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* View Dialog */}
      <Dialog open={!!viewingSample} onOpenChange={() => setViewingSample(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{viewingSample?.title || '歌词详情'}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="flex items-center gap-2 mb-4 text-sm text-gray-600">
              <span>作词人：{viewingSample?.lyricist_name}</span>
              {viewingSample?.source && <span>来源：{viewingSample.source}</span>}
              {viewingSample?.quality_score && (
                <span>质量分：{viewingSample.quality_score.toFixed(2)}</span>
              )}
            </div>
            <pre className="whitespace-pre-wrap text-sm bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
              {viewingSample?.content}
            </pre>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateOpen || !!editingSample} onOpenChange={(open) => {
        if (!open) {
          setIsCreateOpen(false)
          setEditingSample(null)
          resetForm()
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingSample ? '编辑歌词样本' : '添加歌词样本'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[60vh] overflow-y-auto">
            <div className="space-y-2">
              <Label htmlFor="lyricist">作词人 *</Label>
              <select
                id="lyricist"
                className="w-full px-3 py-2 border rounded-md bg-white dark:bg-gray-800"
                value={formData.lyricist_id || selectedLyricistId || ''}
                onChange={(e) => setFormData({ ...formData, lyricist_id: Number(e.target.value) })}
              >
                <option value="">请选择...</option>
                {lyricists?.map((l) => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="title">标题</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="歌曲标题"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="content">歌词内容 *</Label>
              <Textarea
                id="content"
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="歌词内容..."
                rows={10}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="source">来源</Label>
              <Input
                id="source"
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                placeholder="如：网易云音乐、手动录入"
              />
            </div>
            <div className="space-y-2">
              <Label>标签</Label>
              <div className="flex gap-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  placeholder="输入标签"
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                />
                <Button type="button" variant="outline" onClick={addTag}>添加</Button>
              </div>
              {formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {formData.tags.map((tag) => (
                    <span 
                      key={tag} 
                      className="px-2 py-1 bg-purple-100 text-purple-600 rounded text-sm flex items-center gap-1"
                    >
                      {tag}
                      <button onClick={() => removeTag(tag)} className="hover:text-red-500">×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsCreateOpen(false)
              setEditingSample(null)
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
