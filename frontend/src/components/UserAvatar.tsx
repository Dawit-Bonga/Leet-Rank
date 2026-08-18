import { initials } from "../lib/format";

interface UserAvatarProps {
  name: string;
  size?: "sm" | "md" | "lg";
  highlighted?: boolean;
}

const sizes = {
  sm: "size-9 text-[0.65rem]",
  md: "size-11 text-xs",
  lg: "size-16 text-lg",
};

export function UserAvatar({
  name,
  size = "md",
  highlighted = false,
}: UserAvatarProps) {
  return (
    <div
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full border font-black ${sizes[size]} ${
        highlighted
          ? "border-orange-400/30 bg-orange-400/12 text-orange-200 shadow-lg shadow-orange-500/10"
          : "border-white/8 bg-slate-800/80 text-slate-300"
      }`}
    >
      {initials(name)}
    </div>
  );
}
