"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
};

export default function MarkdownContent({ content }: Props) {
  return (
    <div className="markdownContent">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ node, ...props }) {
            void node;
            return <a {...props} target="_blank" rel="noreferrer" />;
          },
          table({ node, ...props }) {
            void node;
            return (
              <div className="markdownTableWrap">
                <table {...props} />
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
