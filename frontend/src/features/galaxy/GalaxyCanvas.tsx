import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo, useState } from "react";
import { BufferAttribute, BufferGeometry, Color } from "three";

import { buildGalaxyScene } from "@/features/galaxy/galaxyScene";
import type { GalaxyFilters, GalaxySnapshot } from "@/features/galaxy/types";

interface GalaxyCanvasProps {
  snapshot: GalaxySnapshot;
  filters: GalaxyFilters;
  onSelectNode?: (nodeId: string | null) => void;
}

export function GalaxyCanvas({ snapshot, filters, onSelectNode }: GalaxyCanvasProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const sceneData = useMemo(() => buildGalaxyScene(snapshot, filters), [snapshot, filters]);

  if (sceneData.nodes.length === 0) {
    return <div className="galaxy-status">No galaxy nodes are currently available.</div>;
  }

  return (
    <div className="galaxy-canvas-shell" data-testid="galaxy-canvas-shell">
      <div className="galaxy-status" data-testid="galaxy-scene-stats">
        Nodes: {sceneData.nodes.length} | Edges: {sceneData.edges.length}
      </div>
      <Canvas
        camera={{ position: [0, 0, 160], fov: 52 }}
        onPointerMissed={() => {
          setSelectedNodeId(null);
          onSelectNode?.(null);
        }}
      >
        <color attach="background" args={["#ffffff"]} />
        <ambientLight intensity={0.45} />
        <pointLight position={[80, 80, 120]} intensity={1.2} />
        <OrbitControls enablePan enableRotate enableZoom dampingFactor={0.08} />
        <EdgeLayer sceneData={sceneData} />
        {sceneData.nodes.map((node) => {
          const isSelected = selectedNodeId === node.id;
          const isHovered = hoveredNodeId === node.id;
          const color = isSelected ? "#d77601" : isHovered ? "#6a8eae" : "#1b365d";
          return (
            <mesh
              key={node.id}
              position={[node.position.x, node.position.y, node.position.z]}
              onPointerOver={(event) => {
                event.stopPropagation();
                setHoveredNodeId(node.id);
              }}
              onPointerOut={(event) => {
                event.stopPropagation();
                setHoveredNodeId((current) => (current === node.id ? null : current));
              }}
              onClick={(event) => {
                event.stopPropagation();
                setSelectedNodeId(node.id);
                onSelectNode?.(node.id);
              }}
            >
              <sphereGeometry args={[Math.max(0.5, node.star_size * 0.3), 12, 12]} />
              <meshStandardMaterial color={color} emissive={new Color(color)} emissiveIntensity={node.star_brightness * 0.3} />
            </mesh>
          );
        })}
      </Canvas>
    </div>
  );
}

function EdgeLayer({ sceneData }: { sceneData: ReturnType<typeof buildGalaxyScene> }) {
  const geometry = useMemo(() => {
    const vertices = new Float32Array(sceneData.edges.length * 6);
    sceneData.edges.forEach((edge, index) => {
      const sourceNode = sceneData.nodeById.get(edge.source);
      const targetNode = sceneData.nodeById.get(edge.target);
      if (!sourceNode || !targetNode) {
        return;
      }
      const base = index * 6;
      vertices[base] = sourceNode.position.x;
      vertices[base + 1] = sourceNode.position.y;
      vertices[base + 2] = sourceNode.position.z;
      vertices[base + 3] = targetNode.position.x;
      vertices[base + 4] = targetNode.position.y;
      vertices[base + 5] = targetNode.position.z;
    });
    const bufferGeometry = new BufferGeometry();
    bufferGeometry.setAttribute("position", new BufferAttribute(vertices, 3));
    return bufferGeometry;
  }, [sceneData.edges, sceneData.nodeById]);

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color="#6a8eae" transparent opacity={0.35} />
    </lineSegments>
  );
}
