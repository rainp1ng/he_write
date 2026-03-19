'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { generationApi, modelApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'

interface Model {
  id: number
  name: string
  status: string
}

export default function GenerationPage() {
  const searchParams = useSearchParams()
  const modelIdParam = searchParams.get('model_id')
  
  const [models, setModels] = useState<Model[]>([])
  const [selectedModelId, setSelectedModelId] = useState<number | null>(
    modelIdParam ? parseInt(modelIdParam) : null
  )
  const [inputText, setInputText] = useState('')
  const [mode, setMode] = useState<'continue' | 'topic' | 'random'>('random')
  const [temperature, setTemperature] = useState(0.9)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState('')

  useEffect(() => {
    loadModels()
  }, [])

  const loadModels = async () => {
    try {
      const res = await modelApi.list({ status: 'completed' })
      setModels(res.data || [])
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const handleGenerate = async () => {
    if (!selectedModelId) {
      alert('请先选择模型')
      return
    }

    setGenerating(true)
    setResult('')

    try {
      const res = await generationApi.generate({
        model_id: selectedModelId,
        input_text: inputText || undefined,
        mode: mode,
        config: {
          temperature: temperature,
          max_length: 256
        }
      })
      setResult(res.data?.output_text || '')
    } catch (error) {
      console.error('Failed to generate:', error)
      setResult('生成失败，请重试')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">歌词创作</h1>

      <div className="grid gap-6 md:grid-cols-2">
        {/* 左侧：配置 */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>选择模型</CardTitle>
            </CardHeader>
            <CardContent>
              <select
                className="w-full p-2 border rounded"
                value={selectedModelId || ''}
                onChange={(e) => setSelectedModelId(parseInt(e.target.value))}
              >
                <option value="">请选择模型</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>生成模式</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button
                  variant={mode === 'random' ? 'default' : 'outline'}
                  onClick={() => setMode('random')}
                >
                  随机生成
                </Button>
                <Button
                  variant={mode === 'topic' ? 'default' : 'outline'}
                  onClick={() => setMode('topic')}
                >
                  主题模式
                </Button>
                <Button
                  variant={mode === 'continue' ? 'default' : 'outline'}
                  onClick={() => setMode('continue')}
                >
                  续写模式
                </Button>
              </div>
            </CardContent>
          </Card>

          {(mode === 'topic' || mode === 'continue') && (
            <Card>
              <CardHeader>
                <CardTitle>
                  {mode === 'topic' ? '输入主题' : '输入提示文本'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  placeholder={mode === 'topic' ? '例如：爱情、梦想...' : '输入开头的歌词...'}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  rows={3}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>创意度: {temperature.toFixed(1)}</CardTitle>
            </CardHeader>
            <CardContent>
              <Slider
                min={0.1}
                max={2.0}
                step={0.1}
                value={[temperature]}
                onValueChange={(v) => setTemperature(v[0])}
              />
              <div className="flex justify-between text-sm text-gray-500 mt-2">
                <span>保守</span>
                <span>创意</span>
              </div>
            </CardContent>
          </Card>

          <Button
            className="w-full"
            size="lg"
            onClick={handleGenerate}
            disabled={generating || !selectedModelId}
          >
            {generating ? '创作中...' : '开始创作'}
          </Button>
        </div>

        {/* 右侧：结果 */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>生成结果</CardTitle>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="whitespace-pre-wrap bg-gray-50 p-4 rounded min-h-[300px]">
                {result}
              </div>
            ) : (
              <div className="text-gray-400 text-center py-20">
                选择模型并点击"开始创作"
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
