import { OrbitControls, Stars } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo, useState } from "react";
import { BufferAttribute, BufferGeometry, Color, FogExp2 } from "three";

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
      <div className="galaxy-scene-stats" data-testid="galaxy-scene-stats">
        <span className="galaxy-scene-stats__nodes">{sceneData.nodes.length} stars</span>
        <span className="galaxy-scene-stats__sep" aria-hidden>
          ·
        </span>
        <span className="galaxy-scene-stats__edges">{sceneData.edges.length} links</span>
      </div>
      <Canvas
        camera={{ position: [0, 0, 160], fov: 52 }}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
        onCreated={({ scene }) => {
          scene.fog = new FogExp2("#030712", 0.00135);
        }}
        onPointerMissed={() => {
          setSelectedNodeId(null);
          onSelectNode?.(null);
        }}
      >
        <color attach="background" args={["#030712"]} />
        <Stars radius={420} depth={80} count={9000} factor={5} saturation={0.12} fade speed={0.4} />
        <ambientLight intensity={0.22} color="#7dd3fc" />
        <pointLight position={[120, 90, 140]} intensity={2.4} color="#fef3c7" />
        <pointLight position={[-100, -60, 80]} intensity={0.85} color="#a78bfa" />
        <OrbitControls enablePan enableRotate enableZoom dampingFactor={0.08} />
        <EdgeLayer sceneData={sceneData} />
        {sceneData.nodes.map((node) => {
          const isSelected = selectedNodeId === node.id;
          const isHovered = hoveredNodeId === node.id;
          const core = isSelected ? "#fbbf24" : isHovered ? "#67e8f9" : "#93c5fd";
          const glow = isSelected ? "#f59e0b" : isHovered ? "#22d3ee" : "#3b82f6";
          const radius = Math.max(0.55, node.star_size * 0.34);
          const emissiveBoost = 0.35 + node.star_brightness * 1.15;
          return (
            <group key={node.id} position={[node.position.x, node.position.y, node.position.z]}>
              <mesh
                scale={1.55}
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
                <sphereGeometry args={[radius, 12, 12]} />
                <meshBasicMaterial transparent opacity={0} depthWrite={false} />
              </mesh>
              <mesh raycast={() => null} scale={1.45}>
                <sphereGeometry args={[radius, 14, 14]} />
                <meshBasicMaterial color={glow} transparent opacity={0.14} depthWrite={false} />
              </mesh>
              <mesh raycast={() => null}>
                <sphereGeometry args={[radius, 20, 20]} />
                <meshStandardMaterial
                  color={core}
                  emissive={new Color(core)}
                  emissiveIntensity={emissiveBoost}
                  metalness={0.35}
                  roughness={0.25}
                />
              </mesh>
            </group>
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
      <lineBasicMaterial color="#5eead4" transparent opacity={0.55} linewidth={1} />
    </lineSegments>
  );
}
