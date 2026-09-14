#import bevy_ui::ui_vertex_output::UiVertexOutput

@group(1) @binding(0) var<uniform> clock: vec4<f32>;
@group(1) @binding(1) var<uniform> pen: vec4<f32>;
@group(1) @binding(2) var ink: texture_2d<f32>;
@group(1) @binding(3) var ink_sampler: sampler;

@fragment
fn fragment(in: UiVertexOutput) -> @location(0) vec4<f32> {
    let t = clock.x;
    let reduced = clock.y > 0.5;
    let uv = in.uv;
    let texel = textureSample(ink, ink_sampler, uv);
    let written_at = (texel.r * 65280.0 + texel.g * 255.0) / 65535.0 * 6.3;
    let coverage = texel.a * smoothstep(written_at, written_at + 0.012, t);
    let recent = exp(-max(t - written_at, 0.0) * 8.0);
    let rose = mix(vec3<f32>(0.95, 0.70, 0.84), vec3<f32>(1.0, 0.95, 0.76), recent * 0.9);
    var color = rose * coverage;
    var alpha = coverage;
    if !reduced {
        let p = (uv - vec2<f32>(0.5)) * vec2<f32>(2.0, 1.0);
        let impact = max(t - 6.5, 0.0);
        let burst = select(0.0, exp(-impact * 2.2), t >= 6.5);
        let angle = atan2(p.y, p.x);
        let rays = pow(abs(sin(angle * 13.0 + 0.3)), 24.0);
        let edge = smoothstep(0.0, 0.12, min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y)));
        let halo = exp(-length(p) * 2.3) * burst * edge;
        let glow = halo * (0.12 + rays * 0.32);
        color += vec3<f32>(0.88, 0.40, 0.14) * glow * (1.0 - coverage);
        alpha = max(alpha, glow);
        // Comically grand gold and pink stars burst out when the signature lands.
        for (var i = 0u; i < 30u; i += 1u) {
            let fi = f32(i);
            let theta = fi * 2.399963;
            let velocity = vec2<f32>(cos(theta), sin(theta));
            let center = velocity * (0.06 + impact * (0.2 + fract(fi * 0.618) * 0.5));
            let delta = p - center;
            let radius = 0.003 + 0.004 * fract(fi * 0.37);
            let star = max(0.0, 1.0 - min(abs(delta.x) * 5.0 + abs(delta.y), abs(delta.y) * 5.0 + abs(delta.x)) / radius);
            let shine = star * burst;
            color += vec3<f32>(1.0, 0.65 + 0.2 * sin(fi), 0.65) * shine;
            alpha = max(alpha, shine);
        }
        // A feather quill follows the same stroke trajectory as the revealed ink.
        if t >= 0.7 && t < 6.3 {
            let delta = (uv - pen.xy) * vec2<f32>(2.0, 1.0);
            let axis = normalize(vec2<f32>(0.65, -0.76));
            let along = dot(delta, axis);
            let across = dot(delta, vec2<f32>(-axis.y, axis.x));
            let taper = sin(clamp((along - 0.018) / 0.19, 0.0, 1.0) * 3.141593);
            let feather = (1.0 - smoothstep(0.0, 0.002, abs(across) - taper * 0.034))
                * step(0.018, along) * (1.0 - step(0.208, along));
            let shaft = (1.0 - smoothstep(0.001, 0.003, abs(across)))
                * step(0.0, along) * (1.0 - step(0.207, along));
            let ribs = 0.82 + 0.18 * sin(along * 650.0 + abs(across) * 150.0);
            let quill = max(feather * ribs, shaft);
            color = mix(color, vec3<f32>(0.98, 0.89, 0.73) * ribs, quill);
            alpha = max(alpha, quill);
            let nib = exp(-length(delta) * 360.0) * pen.z;
            color += vec3<f32>(1.0, 0.72, 0.36) * nib;
            alpha = max(alpha, nib);
        }
    }
    return vec4<f32>(color / max(alpha, 0.00001), clamp(alpha, 0.0, 1.0));
}
