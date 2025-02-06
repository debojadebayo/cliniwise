import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";
import { PdfFocusProvider } from "~/context/pdf";

import type { ChangeEvent } from "react";
import { ViewPdf } from "~/components/pdf-viewer/ViewPdf";
import { backendUrl } from "src/config";
import { MESSAGE_STATUS } from "~/types/conversation";
import type { Message } from "~/types/conversation";
import useMessages from "~/hooks/useMessages";
import { backendClient } from "~/api/backend";
import { RenderConversations as RenderConversations } from "~/components/conversations/RenderConversations";
import { BiArrowBack } from "react-icons/bi";
import type { ClinicalDocument } from "~/types/document";
import { FiShare } from "react-icons/fi";
import ShareLinkModal from "~/components/modals/ShareLinkModal";
import { BsArrowUpCircle } from "react-icons/bs";
import { useModal } from "~/hooks/utils/useModal";
import useIsMobile from "~/hooks/utils/useIsMobile";

export default function Conversation() {
  const router = useRouter();
  const { id } = router.query;

  const { isOpen: isShareModalOpen, toggleModal: toggleShareModal } =
    useModal();

  const { isMobile } = useIsMobile();

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isMessagePending, setIsMessagePending] = useState(false);
  const [userMessage, setUserMessage] = useState("");
  const [selectedDocuments, setSelectedDocuments] = useState<
    ClinicalDocument[]
  >([]);
  const { messages, userSendMessage, systemSendMessage, setMessages } =
    useMessages(conversationId || "");

  const textFocusRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    // router can have multiple query params which would then return string[]
    if (id && typeof id === "string") {
      setConversationId(id);
    }
  }, [id]);

  useEffect(() => {
    const fetchConversation = async (id: string) => {
      try {
        const result = await backendClient.fetchConversation(id);
        if (result.messages) {
          setMessages(result.messages);
        }
        if (result.documents) {
          setSelectedDocuments(result.documents);
        }
      } catch (error) {
        console.error("Failed to fetch conversation:", error);
        router.push("/"); // Redirect to home on error
      }
    };
    if (conversationId) {
      void fetchConversation(conversationId);
    }
  }, [conversationId, setMessages, router]);

  const renderPdfViewer = () => {
    if (!selectedDocuments || selectedDocuments.length === 0) {
      return (
        <div className="flex h-full items-center justify-center">
          <p className="text-gray-500">No documents selected</p>
        </div>
      );
    }

    return (
      <div className="h-full overflow-hidden">
        {selectedDocuments.map((doc) => (
          <ViewPdf key={doc.id} file={doc} />
        ))}
      </div>
    );
  };

  // Keeping this in this file for now because this will be subject to change
  const submit = () => {
    if (!userMessage || !conversationId) {
      return;
    }

    setIsMessagePending(true);
    userSendMessage(userMessage);
    setUserMessage("");

    const messageEndpoint =
      backendUrl + `api/conversation/${conversationId}/message`;
    const url = messageEndpoint + `?user_message=${encodeURI(userMessage)}`;

    const events = new EventSource(url);
    events.onmessage = (event: MessageEvent) => {
      const parsedData: Message = JSON.parse(event.data);
      systemSendMessage(parsedData);

      if (
        parsedData.status === MESSAGE_STATUS.SUCCESS ||
        parsedData.status === MESSAGE_STATUS.ERROR
      ) {
        events.close();
        setIsMessagePending(false);
      }
    };
  };
  const handleTextChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    setUserMessage(event.target.value);
  };
  useEffect(() => {
    const textarea = document.querySelector("textarea");
    if (textarea) {
      textarea.style.height = "auto";

      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [userMessage]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (!isMessagePending) {
          submit();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [submit]);

  const setSuggestedMessage = useCallback(
    (text: string) => {
      setUserMessage(text);
      if (textFocusRef.current) {
        textFocusRef.current.focus();
      }
    },
    [setUserMessage]
  );

  useEffect(() => {
    if (textFocusRef.current) {
      textFocusRef.current.focus();
    }
  }, []);

  if (isMobile) {
    return (
      <div className="landing-page-gradient-1 relative flex h-screen w-screen items-center justify-center">
        <div className="flex h-min w-3/4 flex-col items-center justify-center rounded border bg-white p-4">
          <div className="text-center text-xl ">
            Sorry, the mobile view of this page is currently a work in progress.
            Please switch to desktop!
          </div>
          <button
            onClick={async () => await router.push("/")}
            className="m-4 rounded border bg-llama-indigo px-8 py-2 font-bold text-white hover:bg-[#3B3775]"
          >
            Back Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <PdfFocusProvider>
      <div className="flex h-screen flex-col">
        <div className="flex items-center justify-between border-b p-4">
          <button
            onClick={async () => await router.push("/")}
            className="flex items-center text-gray-600 hover:text-gray-800"
          >
            <BiArrowBack className="mr-2" />
            Back to Documents
          </button>
          <button
            onClick={toggleShareModal}
            className="flex items-center text-gray-600 hover:text-gray-800"
          >
            <FiShare className="mr-2" />
            Share
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* PDF Viewer Section - Fixed in viewport */}
          <div className="h-full w-1/2 border-r overflow-hidden">
            {renderPdfViewer()}
          </div>

          {/* Chat Section - Scrollable */}
          <div className="flex h-full w-1/2 flex-col">
            {/* Messages - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4">
              <RenderConversations
                messages={messages}
                isMessagePending={isMessagePending}
              />
            </div>

            {/* Input Section - Fixed at bottom */}
            <div className="border-t bg-white p-4">
              <div className="flex items-end">
                <textarea
                  ref={textFocusRef}
                  value={userMessage}
                  onChange={handleTextChange}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (!isMessagePending) {
                        submit();
                      }
                    }
                  }}
                  placeholder="Ask a question..."
                  className="mr-2 h-10 flex-1 resize-none rounded border p-2"
                  disabled={isMessagePending}
                />
                <button
                  onClick={submit}
                  disabled={isMessagePending || !userMessage}
                  className={`flex h-10 items-center rounded px-4 ${
                    isMessagePending || !userMessage
                      ? "cursor-not-allowed bg-gray-300"
                      : "bg-llama-indigo text-white hover:bg-[#3B3775]"
                  }`}
                >
                  <BsArrowUpCircle className="mr-2" />
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>

        {isShareModalOpen && (
          <ShareLinkModal
            isOpen={isShareModalOpen}
            toggleModal={toggleShareModal}
          />
        )}
      </div>
    </PdfFocusProvider>
  );
}
