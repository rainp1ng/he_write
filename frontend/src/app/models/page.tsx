'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { modelApi, lyricistApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Model {
  id: number
  name: string
  lyricist_id: number
  status: string
  created_at: string
  trained_at?: string
}

interface Lyricist {
  id: number
  name: string
}

export default function ModelsPage() {
  const router = useRouter()
  const [models, setModels] = useState<Model[]>([])
  const [lyricists, setLyricists] = useState<Lyricist[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [modelsRes, lyricistsRes] = await Promise.all([
        modelApi.list(),
        lyricistApi.list()
      ])
      setModels(modelsRes.data || [])
      setLyricists(lyricistsRes.data || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateModel = async (lyricistId: number, name: string) => {
    try {
      await modelApi.create({
        lyricist_id: lyricistId,
        name: name
      })
      loadData()
    } catch (error) {
      console.error('Failed to create model:', error)
    }
  }

  const handleTrain = async (modelId: number) => {
    try {
      // TODO: Call training API
      console.log('Training model:', modelId)
    } catch (error) {
      console.error('Failed to train model:', error)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">加载中...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">模型管理</h1>
        <Button onClick={() => {
          const lyricistId = prompt('输入作词人ID:')
          const name = prompt('输入模型名称:')
          if (lyricistId && name) {
            handleCreateModel(parseInt(lyricistId), name)
          }
        }}>
          创建模型
        </Button>
      </div>

      <div className="grid gap-4">
        {models.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center text-gray-500">
              暂无模型，请先创建作词人并采集歌词样本
            </CardContent>
          </Card>
        ) : (
          models.map((model) => (
            <Card key={model.id}>
              <CardHeader>
                <CardTitle className="flex justify-between">
                  <span>{model.name}</span>
                  <span className={`text-sm ${
                    model.status === 'completed' ? 'text-green-600' :
                    model.status === 'training' ? 'text-blue-600' :
                    'text-gray-500'
                  }`}>
                    {model.status === 'completed' ? '已完成' :
                     model.status === 'training' ? '训练中' :
                     model.status === 'failed' ? '失败' : '待训练'}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center">
                  <div className="text-sm text-gray-500">
                    <p>作词人ID: {model.lyricist_id}</p>
                    <p>创建时间: {new Date(model.created_at).toLocaleString()}</p>
                    {model.trained_at && (
                      <p>训练时间: {new Date(model.trained_at).toLocaleString()}</p>
                    )}
                  </div>
                  <div className="space-x-2">
                    {model.status === 'pending' && (
                      <Button onClick={() => handleTrain(model.id)}>
                        开始训练
                      </Button>
                    )}
                    {model.status === 'completed' && (
                      <Button 
                        variant="outline"
                        onClick={() => router.push(`/generation?model_id=${model.id}`)}
                      >
                        开始创作
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
