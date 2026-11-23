import { useState } from 'react'
import { Background, Controls, MarkerType, MiniMap, ReactFlow, useNodesState } from '@xyflow/react'
import type { Node } from '@xyflow/react'
import type { Trail } from './api'
import { inr } from './ui'
import '@xyflow/react/dist/style.css'

export default function TrailGraph({ trail }: { trail: Trail }) {
  const rows = new Map<number, number>()
  const initialNodes: Node[] = trail.nodes.map(node => {
    const row = rows.get(node.tier) ?? 0
    rows.set(node.tier, row + 1)
    return {
      id: node.id, position: { x: node.tier * 290, y: row * 125 },
      data: { label: `${node.id}\n${node.freeze_priority ? 'Review balance: ' : 'Recorded balance: '}${node.balance_remaining === null ? 'Unknown' : inr(node.balance_remaining)}` },
      style: { width: 220, whiteSpace: 'pre-line', background: node.freeze_priority ? '#fcf1db' : '#fff' },
      ariaLabel: `Account ${node.id}`,
    }
  })
  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [selected, setSelected] = useState('')
  const edges = trail.edges.map(edge => ({
    id: `${edge.source}:${edge.target}`, source: edge.source, target: edge.target,
    label: `${inr(edge.amount)} · ${edge.transfers} transfer${edge.transfers === 1 ? '' : 's'}`,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { strokeWidth: selected && [edge.source, edge.target].includes(selected) ? 3 : 1 },
  }))
  return <div>
    <p className="muted">Drag accounts, pan or zoom. Select an account to highlight its transfers. The table below provides the same records.</p>
    <div style={{ height: 440, border: '1px solid #cad8db', borderRadius: 10 }} aria-label="Interactive transaction diagram">
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} nodesConnectable={false}
        edgesReconnectable={false} fitView minZoom={0.1} maxZoom={2}
        onNodeClick={(_, node) => setSelected(node.id)} onPaneClick={() => setSelected('')}>
        <Background /><Controls /><MiniMap pannable zoomable />
      </ReactFlow>
    </div>
    {selected && <p role="status">Selected account: {selected}</p>}
  </div>
}

